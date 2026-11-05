"""Candidate rejection checks using the actual FCU velocity callback contract."""
from types import SimpleNamespace as NS
from unittest.mock import patch
from geometry_msgs.msg import TwistStamped
from sensor_msgs.msg import LaserScan
from mission_bt.mav_commander import Mav as Commander
from mission_bt.mission_tree import GateAdvance
from gate_advance_braking_candidate_20261007 import BrakedGateAdvance, RUNNING, FAILURE, SUCCESS
import json
from pathlib import Path
import argparse


class Future:
    def __init__(self, state='accepted'):
        self.state = state
    def done(self):
        return self.state != 'pending'
    def result(self):
        if self.state == 'exception':
            raise RuntimeError('lost response')
        return NS(success=self.state == 'accepted')


class Mav:
    _delivery_velocity = Commander._delivery_velocity
    def __init__(self):
        self.t = 1.
        self.node = NS(get_clock=lambda: NS(now=lambda: NS(nanoseconds=round(self.t*1e9))))
        self.xyz = (20., -16., 2.)
        self.speed_cmd = 5.
        self.delivery_inputs = {}
        self.commands = []
        self.speed_requests = []
        self.response = 'accepted'
        self.abort_reason = ''
        self._scan = LaserScan()
        self.observe()
    def observe(self, speed=0., stamp=None):
        stamp = self.t if stamp is None else stamp
        self._scan.header.stamp.sec = int(stamp)
        self._scan.header.stamp.nanosec = round((stamp-int(stamp))*1e9)
        self.delivery_inputs['pose_stamp'] = stamp
        msg = TwistStamped()
        msg.header = self._scan.header
        msg.twist.linear.x = float(speed)
        self._delivery_velocity(msg)
    def pos(self): return self.xyz
    def yaw(self): return 0.
    def goto(self, *args): self.commands.append(args[:3])
    def set_speed(self, speed):
        self.speed_cmd = speed
        self.speed_requests.append(speed)
        if self.response == 'unavailable': return None
        if self.response == 'service_exception': raise RuntimeError('offline')
        return Future(self.response)


results = []
def record(name, fn):
    fn()
    results.append(dict(name=name, passed=True))

def actor():
    mav = Mav()
    leaf = BrakedGateAdvance(mav, gate_speed_mps=.5)
    leaf.initialise()
    leaf._target = (16., -15.)
    leaf._flight_alt = 2.
    leaf.router = NS(fly=lambda *args: None)
    return mav, leaf

for response in ('rejected', 'exception', 'unavailable', 'service_exception'):
    def reject(response=response):
        mav, leaf = actor()
        mav.response = response
        with patch.object(GateAdvance, 'update', return_value=SUCCESS) as crossing:
            assert leaf.update() == FAILURE
            crossing.assert_not_called()
        assert mav.commands[-1] == mav.xyz
    record('admission_'+response, reject)

def ack_timeout():
    mav, leaf = actor(); mav.response = 'pending'
    with patch.object(GateAdvance, 'update', return_value=SUCCESS) as crossing:
        assert leaf.update() == RUNNING
        mav.t = 4.1; mav.observe()
        assert leaf.update() == FAILURE
        crossing.assert_not_called()
record('admission_ack_timeout', ack_timeout)

def stale_mid_crossing():
    mav, leaf = actor()
    with patch.object(GateAdvance, 'update', return_value=RUNNING):
        assert leaf.update() == RUNNING
        mav.t = 2.; mav.xyz = (16., -15., 2.); mav.observe()
        mav._scan.header.stamp.sec = 1
        assert leaf.update() == FAILURE
        assert mav.commands[-1] == (16., -15., 2.)
        assert mav.commands[-1] != (20., -16., 2.)
record('stale_scan_holds_latest_measured_pose', stale_mid_crossing)

def stale_pose():
    mav, leaf = actor()
    with patch.object(GateAdvance, 'update', return_value=RUNNING):
        assert leaf.update() == RUNNING
        mav.t = 1.1; mav.xyz = (19.9, -16., 2.); mav.observe()
        assert leaf.update() == RUNNING
        mav.t = 2.; mav.xyz = (999., 999., 2.)
        assert leaf.update() == FAILURE
        assert mav.commands[-1] == (19.9, -16., 2.)
record('stale_pose_preserves_last_fresh_stop_anchor', stale_pose)

def distinct_settling_and_restoration():
    mav, leaf = actor()
    with patch.object(GateAdvance, 'update', return_value=SUCCESS):
        assert leaf.update() == RUNNING
        for _ in range(6):
            mav.t += .02
            assert leaf.update() == RUNNING
        assert leaf._settle_count == 1
        for stamp in (1.2, 1.4):
            mav.t = stamp; mav.observe()
            status = leaf.update()
        assert status == SUCCESS
        assert mav.speed_requests == [.5, 5.]
record('distinct_velocity_samples_and_acknowledged_previous_cap_restore', distinct_settling_and_restoration)

def restored_ack_rejection():
    mav, leaf = actor()
    with patch.object(GateAdvance, 'update', return_value=SUCCESS):
        assert leaf.update() == RUNNING
        mav.t = 1.2; mav.observe(); assert leaf.update() == RUNNING
        mav.t = 1.4; mav.observe(); mav.response = 'rejected'
        assert leaf.update() == FAILURE
        assert mav.speed_requests == [.5, 5.]
record('restore_rejection_cannot_report_handover', restored_ack_rejection)

def endless_braking():
    mav, leaf = actor()
    with patch.object(GateAdvance, 'update', return_value=SUCCESS):
        assert leaf.update() == RUNNING
        mav.t = 61.01; mav.observe(speed=1.)
        assert leaf.update() == FAILURE
record('bounded_braking_timeout', endless_braking)

def configured_restore_on_first_gate():
    mav = Mav(); mav.speed_cmd = None
    leaf = BrakedGateAdvance(mav, gate_speed_mps=.5, restore_speed_mps=5.)
    leaf.initialise(); leaf._target=(16., -15.); leaf._flight_alt=2.
    leaf.router=NS(fly=lambda *args: None)
    with patch.object(GateAdvance, 'update', return_value=SUCCESS):
        assert leaf.update()==RUNNING
        mav.t=1.2; mav.observe(); assert leaf.update()==RUNNING
        mav.t=1.4; mav.observe(); assert leaf.update()==SUCCESS
    assert mav.speed_requests==[.5,5.]
    assert leaf._restore_basis.startswith('configured')
record('first_gate_explicit_navigation_restore_configuration', configured_restore_on_first_gate)

def missing_restore_still_fails():
    mav,leaf=actor(); leaf._entry_speed=None
    assert leaf.update()==FAILURE
    assert mav.speed_requests==[]
record('missing_previous_speed_and_configuration_still_rejected', missing_restore_still_fails)

parser=argparse.ArgumentParser()
parser.add_argument('--out',type=Path,default=Path('logs/reliability_gate_braking_fault_checks_20261007.json'))
out=parser.parse_args().out
with out.open('x') as handle:
    json.dump(dict(scope='Candidate interface and fault checks; physical/native qualification separate', cases=results), handle, indent=2)
print(json.dumps(dict(passed=len(results), cases=results)))
