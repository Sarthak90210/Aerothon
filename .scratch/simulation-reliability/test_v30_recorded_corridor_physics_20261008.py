"""Actual navigator and aircraft, initialised from the failed corridor entry.

This isolates the return lane, not ROS arrival ordering or the full mission.
Initial truth/estimate/yaw and wind epoch are recorded. Lidar and estimator
streams are regenerated from the original moderate configuration and seed.
"""
import csv,json,math,random,sys
from pathlib import Path
import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped,TwistStamped
from sensor_msgs.msg import LaserScan
from rclpy.parameter import Parameter
root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'sim'),str(root/'src/aerothon_avoidance/avoidance')]
from avoidance.velocity_controller import VelocityController
from test_headless_land_position_hold import world
from headless_world import Arena,DT,WindDrift,W,LidarCorruptor


def fly(reserve=0.,start_at=None,compute_s=0.,lidar_seed=4,range_bias=0.,full_attitude=False):
    run=root/'logs/reliability_reduced_v30_targeted_20261008/my_world_random_s3'
    rows=[json.loads(s) for s in (run/'onboard.jsonl').open()]
    start=next(r for r in rows if r.get('mission')=='RETURN_CORRIDOR')
    if start_at is not None:start=min((r for r in rows if r.get('mission')=='RETURN_CORRIDOR'),key=lambda r:abs(r['stamp']-start_at))
    truths=list(csv.DictReader((run/'evaluation_truth_track.csv').open()))
    truth=min(truths,key=lambda r:abs(float(r['t_sim'])-start['stamp']))
    w=world();w.t=round(start['stamp'],2);epoch=w.t
    w.p=np.array([float(truth[k]) for k in ('x','y','z')]);p=start['pose']['data']['pose']['position'];q=start['pose']['data']['pose']['orientation']
    w.yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
    w.roll=math.degrees(math.atan2(2*(q['w']*q['x']+q['y']*q['z']),1-2*(q['x']**2+q['y']**2)))
    w.pitch=math.degrees(math.asin(max(-1.,min(1.,2*(q['w']*q['y']-q['z']*q['x'])))))
    w.gps_err=np.array([p['x']-w.p[0],p['y']-w.p[1]]);w.baro_err=p['z']-w.p[2]
    conditions=json.loads((run/'run.json').read_text())['conditions'];wind=conditions['wind']
    w.arena=Arena(W.load(root/'sim/worlds/my_world.json'),'b')
    w.wind=WindDrift(mean=wind['speed'],gust=wind['gust'],period=wind['gust_period_s'],dir_rad=math.radians(wind['dir_deg']),turb=.5*wind['veer_deg']/20*wind['speed']/8,seed=3,dt=DT)
    for i in range(round(epoch/DT)):w.wind(i*DT)
    velocity=start['velocity']['data']['twist']['linear']
    drift=np.array(w.wind(epoch));w.v[:2]=np.array([velocity['x'],velocity['y']])-drift
    w.ground_velocity=np.array([velocity['x'],velocity['y'],velocity['z']])
    w.sp_pos=None;w.sp_vel=(0.,0.,0.,0.,w.t)
    lidar=LidarCorruptor(conditions['lidar'],seed=lidar_seed)
    node=VelocityController();node.enabled=True
    node.set_parameters([Parameter('vel_command_delay_s',value=0.),Parameter('motion_computation_budget_s',value=.20)])
    node._planner.clearance+=reserve
    node._now=lambda:w.t
    def issue(message):
        # The normal runtime measured .05 s in the failing publication.
        # Advance the existing aircraft while that computation occurs;
        # transport and actuator settings remain the recorded 0.0/.6 s.
        for _ in range(round(compute_s/DT)):
            w.t+=DT;w._step_airframe()
        w._on_sp_raw(message)
    node.pub_sp.publish=issue
    node._hold_alt=p['z']
    if start_at is not None:
        observed=start['avoidance']
        node._wind_world=np.array(observed['disturbance_world_mps'])
        node._wind_rate_world=np.array(observed['disturbance_rate_world_mps2'])
        node._ground_world=w.ground_velocity[:2].copy()
        node._expect_world=node._ground_world-node._wind_world
        node._model_t=epoch;node._response_known=True
        node._drift_prev=(p['x'],p['y']);node._drift_prev_t=epoch
        for row in rows:
            if epoch-2<=row['stamp']<epoch and row.get('avoidance'):
                a=row['avoidance'];qq=row['pose']['data']['pose']['orientation']
                heading=math.atan2(2*(qq['w']*qq['z']+qq['x']*qq['y']),1-2*(qq['y']**2+qq['z']**2))
                c,s=math.cos(heading),math.sin(heading)
                cmd=np.array([c*a['cmd_vx']-s*a['cmd_vy_left'],s*a['cmd_vx']+c*a['cmd_vy_left']])
                node._command_history.append((row['stamp'],cmd));node._sent_heading[row['stamp']]=heading
                node._yaw_command_history.append((row['stamp'],a['cmd_yaw_rate']))
    samples=[]
    truth_times=np.array([float(r['t_sim']) for r in truths])
    for row in rows:
        if epoch-1<=row['stamp']<=epoch+70 and row.get('pose'):
            pos=row['pose']['data']['pose']['position'];t=row['stamp']
            true=np.array([np.interp(t,truth_times,[float(r[k]) for r in truths]) for k in ('x','y','z')])
            samples.append((t,np.array([pos[k] for k in ('x','y','z')])-true))
    error_times=np.array([t for t,e in samples]);errors=np.array([e for t,e in samples])
    closest=float('inf');details=None;nextscan=0.;nextcontrol=0.;nextpose=0.
    lane=W.load(root/'sim/worlds/my_world.json')['return_corridor'];axis=math.radians(lane['yaw_deg'])
    mouth=np.array(w.arena.to_local((lane['x'],lane['y'])))
    try:
        for i in range(1,7001):
            error=np.array([np.interp(w.t,error_times,errors[:,k]) for k in range(3)])
            w.gps_err=error[:2];w.baro_err=error[2]
            est=w.est();pose=PoseStamped();pose.header.stamp=w.stamp()
            pose.pose.position.x,pose.pose.position.y,pose.pose.position.z=map(float,est)
            pose.pose.orientation.z=math.sin(w.yaw/2);pose.pose.orientation.w=math.cos(w.yaw/2)
            if full_attitude:
                roll,pitch,yaw=math.radians(w.roll),math.radians(w.pitch),w.yaw
                cr,sr,cp,sp,cy,sy=math.cos(roll/2),math.sin(roll/2),math.cos(pitch/2),math.sin(pitch/2),math.cos(yaw/2),math.sin(yaw/2)
                pose.pose.orientation.w=cr*cp*cy+sr*sp*sy
                pose.pose.orientation.x=sr*cp*cy-cr*sp*sy
                pose.pose.orientation.y=cr*sp*cy+sr*cp*sy
                pose.pose.orientation.z=cr*cp*sy-sr*sp*cy
            if w.t>=nextpose:
                node._on_pose(pose)
                vel=TwistStamped();vel.header.stamp=w.stamp();vel.twist.linear.x,vel.twist.linear.y,vel.twist.linear.z=map(float,w.ground_velocity);node._on_velocity(vel);nextpose=w.t+.03-1e-9
            if w.t>=nextscan:
                ranges=w.arena.raycast(*w.p[:2],w.p[2]+.08,w.yaw)
                scan=LaserScan();scan.header.stamp=w.stamp();scan.header.frame_id='base_link';scan.angle_min=-math.pi;scan.angle_increment=2*math.pi/len(ranges)
                scan.range_min=.05;scan.range_max=12.;scan.ranges=[float(v+range_bias) if np.isfinite(v) else float(v) for v in lidar.apply(ranges,.05,12.)];node._on_scan(scan);nextscan=w.t+.1-1e-9
            if w.t>=nextcontrol:node._tick();nextcontrol+=.05
            w.t+=DT;w._step_airframe()
            gap=min(W.distance_to_edge(w.p[:2],poly) for poly,z0,z1,kind in w.arena.boxes if kind in ('wall','obstacle') and z0<=w.p[2]<=z1)
            if gap<closest:closest=gap;details=dict(t=w.t,position=w.p.tolist(),avoidance=node.last_detail)
            progress=float((w.p[:2]-mouth)@np.array([math.cos(axis),math.sin(axis)]))
            if progress>lane['length']+.3:break
        return dict(clearance=closest,seconds=w.t-epoch,progress=progress,contacts=w.contacts,minimum=details,reserve=reserve)
    finally:node.destroy_node()


def test_recorded_mild_corridor_entry_preserves_required_clearance():
    rclpy.init()
    try:result=fly()
    finally:rclpy.shutdown()
    (root/'logs/reliability_v30_recorded_corridor_physics_baseline_20261008.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    assert result['progress']>10.3
    assert not result['contacts']


def test_recorded_normal_computation_interval_preserves_clearance():
    rclpy.init()
    try:result=fly(compute_s=.05)
    finally:rclpy.shutdown()
    (root/'logs/reliability_v30_recorded_corridor_compute_baseline_20261008.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    assert result['progress']>10.3
    assert result['clearance']>=.70
    assert not result['contacts']


def test_outward_range_uncertainty_cannot_consume_surface_clearance():
    rclpy.init()
    try:result=fly(compute_s=.05,range_bias=.04)
    finally:rclpy.shutdown()
    (root/'logs/reliability_v30_corridor_outward_uncertainty_baseline_20261008.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    assert result['progress']>10.3
    assert result['clearance']>=.70
    assert not result['contacts']


def test_normal_full_attitude_pose_preserves_surface_clearance():
    rclpy.init()
    try:result=fly(compute_s=.05,full_attitude=True)
    finally:rclpy.shutdown()
    (root/'logs/reliability_v30_corridor_full_attitude_baseline_20261008.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    assert result['progress']>10.3
    assert result['clearance']>=.70
    assert not result['contacts']
    assert result['clearance']>=.70


def test_recorded_near_boundary_state_preserves_required_clearance():
    rclpy.init()
    try:result=fly(start_at=764.6)
    finally:rclpy.shutdown()
    (root/'logs/reliability_v30_recorded_corridor_boundary_baseline_20261008.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    assert result['clearance']>=.70
    assert not result['contacts']
