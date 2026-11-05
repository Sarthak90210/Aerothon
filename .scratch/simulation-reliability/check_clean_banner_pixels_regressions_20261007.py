"""Repeat camera regressions with display pixels excluded from all analysis."""
import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'src/aerothon_perception/perception_banner'),str(root/'src/aerothon_mission/mission_bt')]
from perception_banner.banner_node import BannerNode
from clean_banner_pixels_candidate_20261007 import install
out=root/'logs/reliability_clean_banner_pixels_regressions_20261007';out.mkdir(exist_ok=False)
install(BannerNode,out/'source_override')
(out/'runner_source.py').write_bytes(Path(__file__).read_bytes())
import pytest
names=['test_banner_capture_contract.py','test_banner_identity.py','test_banner_sweep.py',
    'test_banner_orbit.py','test_banner_text.py','test_camera_gate.py',
    'test_phase0_rails.py','test_corruption_envelope.py']
assert all((root/'sim'/name).is_file() for name in names)
code=pytest.main(['-q',*[str(root/'sim'/name) for name in names]])
(out/'report.json').write_text(json.dumps(dict(exit_code=code,production_modified=False,
    candidate_sha256=hashlib.sha256((out/'source_override/candidate_on_image.py').read_bytes()).hexdigest(),
    scope='Saved camera fixtures and mission interface regressions; native qualification pending'),indent=2)+'\n')
raise SystemExit(code)
