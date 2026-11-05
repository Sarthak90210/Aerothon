"""Exercise the new saved regression against the exact checked runtime repair."""
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'src/aerothon_perception/perception_banner'),str(root/'src/aerothon_mission/mission_bt')]
from perception_banner.banner_node import BannerNode
from clean_banner_pixels_candidate_20261007 import install
out=root/'logs/reliability_pristine_banner_new_regression_20261007';out.mkdir(exist_ok=False)
install(BannerNode,out/'source_override')
text=(root/'logs/reliability_clean_banner_review_patch_20261007/test_banner_capture_contract.py.candidate').read_text()
old='ROOT=Path(__file__).resolve().parents[1]'
assert text.count(old)==1;text=text.replace(old,'ROOT=Path(__file__).resolve().parents[2]')
test=Path(__file__).with_name('pristine_banner_capture_test_candidate_20261007.py')
assert not test.exists();test.write_text(text)
import pytest
code=pytest.main(['-q',str(test)])
(out/'report.json').write_text(json.dumps(dict(exit_code=code,production_modified=False,
    scope='New camera-pixel regression plus capture contracts, isolated checked function'),indent=2)+'\n')
raise SystemExit(code)
