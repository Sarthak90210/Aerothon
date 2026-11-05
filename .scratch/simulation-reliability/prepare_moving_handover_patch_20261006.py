"""Generate a proposal under .scratch only. Does not apply or execute it."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).resolve().parent

HELPERS = '''def argument_parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--entry',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--wall-timeout',type=float,default=1800)
    default=os.environ.get('AEROTHON_CORRIDOR_HANDOVER','stationary')
    if default not in ('stationary','moving'):p.error('invalid AEROTHON_CORRIDOR_HANDOVER')
    p.add_argument('--handover-mode',choices=('stationary','moving'),
                   default=default)
    return p


class MovingGateHandover:
    """Command the real gate leaf, then enable avoidance on its arrival tick."""
    max_age_s=.7

    def __init__(self,mav,entry):
        self.mav,self.entry=mav,entry
        dx=float(entry['x'])-float(entry['approach']['x'])
        dy=float(entry['y'])-float(entry['approach']['y'])
        if not all(math.isfinite(v) for v in (dx,dy)) or math.hypot(dx,dy)<=.25:
            raise ValueError('moving fixture requires a finite gate approach')
        self.setup_yaw=math.atan2(dy,dx)
        self.velocity=None;self.velocity_received=None;self.leaf=None

    @staticmethod
    def stamp(message):
        return message.header.stamp.sec+message.header.stamp.nanosec*1e-9

    def on_velocity(self,message,received_stamp):
        if self.velocity is not None and self.stamp(message)<=self.stamp(self.velocity):return
        self.velocity,self.velocity_received=message,received_stamp

    def observation(self,now):
        if self.velocity is None:return None
        pose=self.mav.pose;velocity=self.velocity
        stamps=(self.stamp(pose),self.stamp(velocity),self.velocity_received)
        p,q=pose.pose.position,pose.pose.orientation
        v,w=velocity.twist.linear,velocity.twist.angular
        values=(p.x,p.y,p.z,q.x,q.y,q.z,q.w,v.x,v.y,v.z,w.x,w.y,w.z)
        if (not all(math.isfinite(value) for value in (*stamps,*values)) or
                any(stamp<=0 or not 0<=now-stamp<=self.max_age_s for stamp in stamps) or
                q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w<1e-12):return None
        return dict(pose=dict(capture_stamp=stamps[0],frame_id=pose.header.frame_id,
            position=[p.x,p.y,p.z],quaternion=[q.x,q.y,q.z,q.w]),
            velocity=dict(capture_stamp=stamps[1],received_stamp=stamps[2],
                frame_id=velocity.header.frame_id,linear=[v.x,v.y,v.z],angular=[w.x,w.y,w.z]),
            horizontal_speed_mps=math.hypot(v.x,v.y),max_age_s=self.max_age_s)

    def update(self,now):
        from mission_bt.mission_tree import GateAdvance
        import py_trees
        measured=self.observation(now)
        if not self.mav.state.connected or measured is None:
            return dict(state='FAILED',reason='moving handover lacks fresh finite FCU pose/velocity')
        if self.leaf is None:
            x,y,_=self.mav.pos()
            distance=math.hypot(float(self.entry['x'])-x,float(self.entry['y'])-y)
            self.leaf=GateAdvance(self.mav,advance_m=distance,alt=float(self.entry['alt']),
                tol=.25,exclusions=lambda:self.mav.exclusions)
            self.leaf.initialise()
        outcome=self.leaf.update()
        if outcome is py_trees.common.Status.FAILURE:
            return dict(state='FAILED',reason=self.leaf.feedback_message or self.mav.abort_reason)
        if outcome is py_trees.common.Status.SUCCESS:
            self.mav.enable_avoidance(True,hold_alt=float(self.entry['alt']))
            return dict(state='HANDED_OVER',transition_stamp=now,observation=measured,
                gate_target_xy=list(self.leaf._target),arrival_tolerance_m=self.leaf.tol,
                fixture_capture_stamp=self.entry.get('captured_stamp'),
                fixture_source=self.entry.get('source'),fixture_source_sha256=self.entry.get('source_sha256'))
        return dict(state='CROSSING')


'''

TESTS = '''"""Moving focused handover must preserve observed entry motion and real gate semantics.

These are driver seam checks, not flight or sensor qualification.
"""
import math
from types import SimpleNamespace as NS
import pytest
from corridor_trial import MovingGateHandover, argument_parser
from mission_bt.mission_tree import GateAdvance
from test_leg_routing import RoutedMav


def header(t,frame):
    sec=int(t)
    return NS(stamp=NS(sec=sec,nanosec=round((t-sec)*1e9)),frame_id=frame)


def measured(mav,t,linear=(.31,.07,-.003)):
    x,y,z=mav.pos();yaw=mav.yaw()
    mav.pose=NS(header=header(t,'map'),pose=NS(position=NS(x=x,y=y,z=z),
        orientation=NS(x=0.,y=0.,z=math.sin(yaw/2),w=math.cos(yaw/2))))
    return NS(header=header(t,'base_link'),twist=NS(linear=NS(x=linear[0],y=linear[1],z=linear[2]),
        angular=NS(x=0.,y=0.,z=0.)))


def crossing():
    mav=RoutedMav(at=(0.,0.,1.65));mav.state=NS(connected=True,armed=True)
    calls=[];mav.enable_avoidance=lambda on,hold_alt=None:calls.append((on,hold_alt))
    entry=dict(x=5.4,y=0.,alt=1.65,yaw=0.,approach=dict(x=0.,y=0.),captured_stamp=868.408)
    gate=MovingGateHandover(mav,entry)
    gate.on_velocity(measured(mav,10.),10.)
    return mav,gate,calls


def test_default_remains_stationary_and_cli_selects_moving(monkeypatch):
    monkeypatch.delenv('AEROTHON_CORRIDOR_HANDOVER',raising=False)
    assert argument_parser().parse_args(['--entry','entry.json','--out','out']).handover_mode=='stationary'
    assert argument_parser().parse_args(['--entry','entry.json','--out','out','--handover-mode','moving']).handover_mode=='moving'


def test_real_gate_leaf_hands_over_on_arrival_tick_without_three_second_hold():
    mav,gate,calls=crossing()
    assert gate.update(10.)['state']=='CROSSING'
    assert isinstance(gate.leaf,GateAdvance)
    assert all(on is False for on,_ in calls)
    mav._pos=(5.16,0.,1.65);mav._alt=1.65
    velocity=measured(mav,10.15)
    gate.on_velocity(velocity,10.2)
    result=gate.update(10.2)
    assert result['state']=='HANDED_OVER' and result['transition_stamp']==10.2
    assert calls[-1]==(True,1.65)
    assert result['observation']['velocity']['capture_stamp']==10.15
    assert result['observation']['velocity']['linear']==[.31,.07,-.003]
    assert velocity.twist.linear.x==.31
    assert result['arrival_tolerance_m']==.25


def test_environment_selects_moving_and_rejects_unknown_mode(monkeypatch):
    monkeypatch.setenv('AEROTHON_CORRIDOR_HANDOVER','moving')
    assert argument_parser().parse_args(['--entry','entry.json','--out','out']).handover_mode=='moving'
    monkeypatch.setenv('AEROTHON_CORRIDOR_HANDOVER','unknown')
    with pytest.raises(SystemExit):argument_parser()


def test_gate_does_not_handover_before_production_arrival_tolerance():
    mav,gate,calls=crossing();gate.update(10.)
    mav._pos=(5.14,0.,1.65);mav._alt=1.65
    gate.on_velocity(measured(mav,10.2),10.2)
    assert gate.update(10.2)['state']=='CROSSING'
    assert all(on is False for on,_ in calls)


@pytest.mark.parametrize('kind',['stale_pose','stale_velocity','future_pose','nonfinite_velocity','disconnected'])
def test_bad_observations_cannot_command_gate_or_handover(kind):
    mav,gate,calls=crossing()
    if kind=='stale_pose':mav.pose.header=header(9.2,'map')
    if kind=='stale_velocity':gate.velocity.header=header(9.2,'base_link')
    if kind=='future_pose':mav.pose.header=header(10.01,'map')
    if kind=='nonfinite_velocity':gate.velocity.twist.linear.x=float('nan')
    if kind=='disconnected':mav.state.connected=False
    assert gate.update(10.)['state']=='FAILED'
    assert mav.gotos==[] and calls==[]


def test_duplicate_velocity_does_not_refresh_captured_or_received_time():
    mav,gate,calls=crossing()
    original=gate.velocity
    gate.on_velocity(measured(mav,10.,linear=(0.,0.,0.)),10.6)
    assert gate.velocity is original and gate.velocity_received==10.
    measured(mav,10.71)
    assert gate.update(10.71)['state']=='FAILED'
    assert mav.gotos==[] and calls==[]


def test_gate_latches_its_target_and_uses_position_commands_before_handover():
    mav,gate,calls=crossing();gate.update(10.)
    first=gate.leaf._target
    assert mav.gotos[-1][:3]==(5.4,0.,1.65)
    mav._pos=(1.,0.,1.65);mav._alt=1.65
    gate.on_velocity(measured(mav,10.2),10.2);gate.update(10.2)
    assert gate.leaf._target==first
    assert all(on is False for on,_ in calls)
'''


def replace_once(text,old,new):
    assert text.count(old)==1, old[:100]
    return text.replace(old,new,1)


original_driver=(ROOT/'sim/corridor_trial.py').read_text()
driver=replace_once(original_driver,'import math\n','import math\nimport os\n')
driver=replace_once(driver,'def main():\n',HELPERS+'def main():\n')
driver=replace_once(driver,"    p=argparse.ArgumentParser(description=__doc__)\n    p.add_argument('--entry',type=Path,required=True)\n    p.add_argument('--out',type=Path,required=True)\n    p.add_argument('--wall-timeout',type=float,default=1800)\n    args=p.parse_args()",'    p=argument_parser()\n    args=p.parse_args()')
driver=replace_once(driver,'    mav=Mav(node)\n',"    mav=Mav(node)\n    moving=MovingGateHandover(mav,entry) if args.handover_mode=='moving' else None\n    setup_yaw=moving.setup_yaw if moving is not None else yaw\n    if moving is not None:\n        from geometry_msgs.msg import TwistStamped\n        from rclpy.qos import qos_profile_sensor_data\n        node.create_subscription(TwistStamped,'/mavros/local_position/velocity_local',\n            lambda msg:moving.on_velocity(msg,node.get_clock().now().nanoseconds*1e-9),qos_profile_sensor_data)\n")
driver=replace_once(driver,'                mav.goto(ax,ay,10,yaw)\n','                mav.goto(ax,ay,10,setup_yaw)\n')
driver=replace_once(driver,"                mav.goto(ax,ay,z,yaw);mav.set_camera_pose('FORWARD')\n                if mav.reached(ax,ay,z,.12):advance('CROSS_GATE')", "                mav.goto(ax,ay,z,setup_yaw);mav.set_camera_pose('FORWARD')\n                aligned=abs(math.atan2(math.sin(mav.yaw()-setup_yaw),math.cos(mav.yaw()-setup_yaw)))<.01\n                if mav.reached(ax,ay,z,.12) and (moving is None or aligned):advance('CROSS_GATE')")
driver=replace_once(driver,"            elif phase=='CROSS_GATE':\n                mav.goto(x,y,z,yaw)\n                if mav.reached(x,y,z,.12) and abs(math.atan2(math.sin(mav.yaw()-yaw),math.cos(mav.yaw()-yaw)))<.08:\n                    advance('SETTLE_ENTRY')", "            elif phase=='CROSS_GATE':\n                if moving is not None:\n                    handover=moving.update(now)\n                    if handover['state']=='HANDED_OVER':\n                        handover['handover_mode']=args.handover_mode\n                        (args.out/'entry_handover.json').write_text(json.dumps(handover,indent=2)+'\\n')\n                        advance('RETURN_CORRIDOR')\n                    elif handover['state']=='FAILED':\n                        result=dict(state='TRIAL_FAILED',reason=handover['reason'],t=now)\n                        mav.enable_avoidance(False);advance('LAND')\n                else:\n                    mav.goto(x,y,z,yaw)\n                    if mav.reached(x,y,z,.12) and abs(math.atan2(math.sin(mav.yaw()-yaw),math.cos(mav.yaw()-yaw)))<.08:\n                        advance('SETTLE_ENTRY')")
driver=replace_once(driver,"            trace.write(json.dumps(dict(stamp=now,phase=phase,pose=mav.pos(),avoidance=mav.avoid_detail))+'\\n');trace.flush()", "            trace.write(json.dumps(dict(stamp=now,phase=phase,pose=mav.pos(),avoidance=mav.avoid_detail,\n                handover_mode=args.handover_mode,entry_observation=moving.observation(now) if moving is not None else None))+'\\n');trace.flush()")
driver=replace_once(driver,"        result['final_armed']=bool(mav.state.armed)\n", "        result['final_armed']=bool(mav.state.armed)\n        result['handover_mode']=args.handover_mode\n")

original_runner=(ROOT/'scripts/run_recorded_acceptance.sh').read_text()
runner=replace_once(original_runner,'entry="${AEROTHON_CORRIDOR_ENTRY:-}"\n','entry="${AEROTHON_CORRIDOR_ENTRY:-}"\nhandover="${AEROTHON_CORRIDOR_HANDOVER:-stationary}"\ncase "$handover" in stationary|moving) ;; *) echo \'Unknown return handover mode\'; exit 2 ;; esac\n')
runner=replace_once(runner,' python3 - "$out" <<\'PY\'\nimport hashlib,json,sys\n',' python3 - "$out" "$handover" <<\'PY\'\nimport hashlib,json,sys\n')
runner=replace_once(runner,"         entry_fixture_sha256=hashlib.sha256((out/'entry_fixture.json').read_bytes()).hexdigest())", "         entry_fixture_sha256=hashlib.sha256((out/'entry_fixture.json').read_bytes()).hexdigest(),\n         handover_mode=sys.argv[2],handover_max_age_s=.7 if sys.argv[2]=='moving' else None,\n         handover_driver_sha256=hashlib.sha256(Path('sim/corridor_trial.py').read_bytes()).hexdigest())")
runner=replace_once(runner,' python3 -u sim/corridor_trial.py --entry "$out/entry_fixture.json" --out "$out" > "$out/mission.log" 2>&1 || mission_rc=$?', ' python3 -u sim/corridor_trial.py --entry "$out/entry_fixture.json" --out "$out" --handover-mode "$handover" > "$out/mission.log" 2>&1 || mission_rc=$?')

original_grader=(ROOT/'.scratch/simulation-reliability/grade_focused_return.py').read_text()
grader=replace_once(original_grader,"grade=navigation_grade(nav,layout,'b')", "# Keep approach, descent, crossing, recovery and landing samples in the physical clearance check.\ngrade=navigation_grade(track,layout,'b')")
grader=replace_once(grader,"summary=dict(focused_pass=all(checks.values()),checks=checks,", "summary=dict(focused_pass=all(checks.values()),checks=checks,\n    handover_mode=json.loads((out/'configuration.json').read_text()).get('handover_mode','stationary'),\n    clearance_phase_source='all recorded native aircraft samples, including operator approach',")

proposals={
    'sim/corridor_trial.py':(original_driver,driver),
    'scripts/run_recorded_acceptance.sh':(original_runner,runner),
    '.scratch/simulation-reliability/grade_focused_return.py':(original_grader,grader),
    'sim/test_moving_return_handover.py':('',TESTS),
}
patch=''
for name,(old,new) in proposals.items():
    if name.endswith('.py'):
        ast.parse(new, filename=name)
    patch+=''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),
        fromfile='a/'+name if old else '/dev/null',tofile='b/'+name))
    target=DEST/('proposed_'+Path(name).name)
    target.write_text(new)
(DEST/'proposed_moving_handover.patch').write_text(patch)
(DEST/'proposed_moving_handover_base_hashes.json').write_text(json.dumps({name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    for name,(old,_) in proposals.items() if old},indent=2)+'\n')
print(json.dumps(dict(proposal=str(DEST/'proposed_moving_handover.patch'),files=list(proposals),applied=False),indent=2))
