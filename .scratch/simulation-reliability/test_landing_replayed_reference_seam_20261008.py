"""Probe the recorded returning pose/reference in the existing airframe model."""
import csv,json,math,sys
from collections import deque
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'.scratch/simulation-reliability'))
from test_precision_descent_physics_seam_20261008 import CameraAirframe,DT,PrecisionDescent,py_trees,np


class ReplayedAirframe(CameraAirframe):
    def __init__(self):
        super().__init__();w=self.w
        run=root/'logs/reliability_reduced_v20_targeted_20261008/my_world_field_s2'
        rows=[json.loads(s) for s in (run/'onboard.jsonl').open()]
        initial=next(r for r in rows if r.get('mission')=='CAMERA_FWD')
        start=next(r for r in rows if r.get('mission')=='LAND')
        p=initial['pose']['data']['pose']['position'];self.home_marker_xy=(p['x'],p['y'])
        p=start['pose']['data']['pose']['position'];q=start['pose']['data']['pose']['orientation']
        w.yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
        truth=min(csv.DictReader((run/'evaluation_truth_track.csv').open()),key=lambda r:abs(float(r['t_sim'])-start['stamp']))
        w.p=np.array([float(truth[k]) for k in ('x','y','z')]);w.t=start['stamp']
        w.gps_err=np.array([p['x']-w.p[0],p['y']-w.p[1]])
        w.baro_err=p['z']-w.p[2];w.baro_noise=0.;w.sp_pos=(*w.est(),w.yaw)
        self.pending=deque();self.start=w.t
    def step(self,index):
        w=self.w;w.t+=DT;w._step_errors();w._step_airframe()
        if index%5==0 and w.rng.random()>=w.cond['camera']['frame_drop']:
            eye=w.p+np.array([.16*math.cos(w.yaw),.16*math.sin(w.yaw),0.])
            self.pending.append((w.t+.06,w._qr(eye,math.pi/2)['off']))
        while self.pending and self.pending[0][0]<=w.t:self.qr_offset=self.pending.popleft()[1]


def test_recorded_reference_does_not_turn_single_lost_frame_into_climb():
    mav=ReplayedAirframe();leaf=PrecisionDescent(mav,marker_m=3.1,hfov_rad=.851919)
    leaf.initialise();status=py_trees.common.Status.RUNNING
    for index in range(1,12501):
        mav.step(index)
        if index%20==0:
            status=leaf.update()
            if status is not py_trees.common.Status.RUNNING:break
    print(dict(seconds=mav.w.t-mav.start,precision=mav.landing_precision,reference=mav.home_marker_xy,position=mav.pos()))
    assert mav.landing_precision.startswith('PRECISE')
