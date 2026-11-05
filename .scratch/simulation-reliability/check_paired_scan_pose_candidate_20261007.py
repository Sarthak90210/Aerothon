"""Moving and rotating capture-pose registration checks."""
import importlib.util,json,math
from pathlib import Path
path=Path(__file__).with_name('paired_scan_pose_candidate_20261007.py')
spec=importlib.util.spec_from_file_location('paired_scan',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def row(stamp,x,y,yaw):
    return stamp,x,y,yaw,(0.,0.,math.sin(yaw/2),math.cos(yaw/2))
passed=[]
history=[row(1.,0.,0.,math.radians(179)),row(1.1,.1,.2,math.radians(-179))]
pose,q=module.capture_pose(history,1.05)
assert math.dist(pose[:2],(.05,.1))<1e-9 and abs(abs(pose[2])-math.pi)<1e-9
passed.append('scan capture receives interpolated moving position and wrapped rotation')
assert module.capture_pose(history,1.15) is None
passed.append('future capture waits for a later onboard pose rather than nearest-pose extrapolation')
assert module.capture_pose([row(1.,0,0,0),row(1.4,.4,0,0)],1.1) is None
passed.append('missing pose interval cannot place obstacle surfaces')
assert module.capture_pose(history,1.)==(history[0][1:4],history[0][4])
passed.append('exact capture preserves measured pose without interpolation')
new=list(history[1]);new[4]=tuple(-x for x in new[4])
assert math.dist(module.capture_pose([history[0],tuple(new)],1.05)[0][:2],(.05,.1))<1e-9
passed.append('quaternion sign alias does not introduce a full-turn interpolation')
capture=1.05;true_position=.025
history=[row(1.,0.,0.,0.),row(1.1,.05,0.,0.)]
old_pose=min(history,key=lambda r:abs(r[0]-capture))[1]
paired=module.capture_pose(history,capture)[0][0]
assert abs(old_pose-true_position)>.0249 and abs(paired-true_position)<1e-9
passed.append('a half-metre-per-second approach removes a 2.5 cm nearest-pose displacement')
out=path.parents[2]/'logs/reliability_paired_scan_pose_candidate_20261007';out.mkdir(exist_ok=False)
report=dict(checks=passed,count=len(passed),simulator_truth_input=False,
            production_adopted=False,full_flight_qualified=False)
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
(out/path.name).write_bytes(path.read_bytes())
print(json.dumps(report))
