"""Fault and delayed-yaw checks for capture-time banner association."""
import importlib.util
import json
import math
from pathlib import Path
path=Path(__file__).with_name('banner_capture_candidate_20261007.py')
spec=importlib.util.spec_from_file_location('banner_capture',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def history():
    stream=module.BannerCaptures()
    assert stream.pose(1.,(0,0,5),math.radians(179))
    assert stream.pose(1.2,(2,0,5),math.radians(-179))
    return stream

passed=[]
stream=history()
detail=dict(capture_stamp=1.1,processed_stamp=1.3,identified=True,bearing=0.)
assert stream.receive(detail,1.3)
capture=stream.current(1.3)
assert math.dist(capture['pose']['xyz'],(1,0,5))<1e-9
assert abs(abs(capture['pose']['yaw'])-math.pi)<1e-9
passed.append('capture pose interpolates across the yaw wrap')
assert not stream.receive(detail,1.4) and stream.sequence==1
assert not stream.receive(dict(detail,capture_stamp=1.05),1.4) and stream.sequence==1
passed.append('duplicate and reordered messages do not create new frames')
assert stream.current(1.3,not_before=1.15) is None
passed.append('frames captured before a dwell cannot count toward that dwell')
assert stream.current(1.9) is None
passed.append('latched sightings expire without a replacement message')
stream=history();assert not stream.receive(dict(detail,capture_stamp=2.),1.3)
passed.append('future captures cannot qualify')
stream=history();assert not stream.receive({'identified':True},1.3)
passed.append('unstamped legacy status cannot qualify')
stream=history();assert stream.receive(dict(detail,capture_stamp=1.25),1.4)
assert stream.current(1.4) is None
assert stream.pose(1.3,(3,0,5),math.radians(-178))
assert stream.current(1.4) is not None
passed.append('unpaired captures wait for onboard pose rather than extrapolating')
stream=module.BannerCaptures();stream.pose(1.,(0,0,5),0.)
stream.pose(1.6,(0,0,5),0.)
assert stream.receive(dict(detail,capture_stamp=1.3,processed_stamp=1.6),1.6)
assert stream.current(1.6) is None
passed.append('missing pose interval refuses geometric projection')
stream=module.BannerCaptures();stream.pose(1.,(0,0,5),0.)
assert stream.receive(dict(detail,capture_stamp=1.,processed_stamp=1.3),1.3)
fov=math.radians(60)
assert abs(stream.bearing_now(1.3,math.radians(15),fov)-
           math.tan(math.radians(15))/math.tan(fov/2))<1e-9
assert stream.bearing_now(1.3,math.radians(40),fov) is None
passed.append('delayed detection retains the captured world ray after yaw')
out=path.parents[2]/'logs/reliability_banner_capture_candidate_20261007'
out.mkdir(exist_ok=False)
report=dict(passed=passed,count=len(passed),production_adopted=False,
            simulator_truth_input=False,rendered_qualified=False)
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
(out/path.name).write_bytes(path.read_bytes())
print(json.dumps(report))
