"""Use repeated clipped identity as a bearing, never as an area-based distance."""
import inspect
import json
import sys
import textwrap
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'src/aerothon_mission/mission_bt'),str(root/'sim')]
from mission_bt.mission_tree import AlignToBanner
from test_banner_sweep import Clock,SweepMav
from mission_bt.scan_geometry import bearing_to_angle
variant=sys.argv[1];assert variant in ('before','after','regressions')
out=root/f'logs/reliability_clipped_banner_bearing_{variant}_20261007';out.mkdir(exist_ok=False)
before=textwrap.dedent(inspect.getsource(AlignToBanner._dwell))
anchor='    rng = self.range_from_area(self._best_area)'
assert before.count(anchor)==1
after=before.replace(anchor,'''    if self._confident(ratio) and self._clipped >= self.min_samples:
        # A cropped board supplies a camera bearing, but its missing pixels
        # cannot supply the distance needed to label it a far gate. Turn at
        # the current anchor to recover a centred view; subsequent alignment
        # and crossing still require the original camera/lidar checks.
        correction=bearing_to_angle(self._best_bearing or 0.0,self.hfov)
        self.mav.log('AlignToBanner: repeated clipped identity; centring bearing before range assessment')
        return self._accept_heading(self._wrap(self._target_yaw+correction))
'''+anchor)
(out/'original_dwell.py').write_text(before);(out/'candidate_dwell.py').write_text(after)
if variant!='before':
    namespace=dict(AlignToBanner._dwell.__globals__)
    exec(compile(after,str(out/'candidate_dwell.py'),'exec'),namespace)
    AlignToBanner._dwell=namespace['_dwell']
if variant=='regressions':
    import pytest
    code=pytest.main(['-q',*[str(root/'sim'/name) for name in ('test_banner_sweep.py','test_banner_orbit.py','test_banner_capture_contract.py','test_camera_gate.py','test_return_gate_search.py')]])
    (out/'report.json').write_text(json.dumps(dict(exit_code=int(code),production_modified=False))+'\n')
    raise SystemExit(code)
clock=Clock();mav=SweepMav(banner_at=0.)
mav.banner_clipped=True;mav.banner_board_area=100.
mav.banner_bearing=lambda:.7
stage=AlignToBanner(mav,clock=clock);stage.initialise()
stage._anchor=mav.pos();stage._target_yaw=0.;stage._enter(stage.DWELL)
accepted=[]
stage._accept_heading=lambda yaw:accepted.append(yaw)
for _ in range(40):
    clock.advance(.2);stage._dwell()
    if accepted:break
expected=bearing_to_angle(.7,stage.hfov)
passed=bool(accepted) and abs(accepted[0]-expected)<1e-9 and all(g[:3]==stage._anchor for g in mav.gotos)
report=dict(passed=passed,accepted_headings=accepted,expected_bearing_correction=expected,
    area_range_estimate_m=stage.range_from_area(100.),near_range_limit_m=stage.near_range_m,
    production_modified=False,scope='Actual dwell method with repeated clipped camera classification; turn only, no crossing qualification')
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
raise SystemExit(0 if passed else 1)
