"""Before/after real callback regression; production files remain unchanged."""
import json
import sys
from pathlib import Path
import pytest

root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root/'src/aerothon_mission/mission_bt'), str(root/'sim'),
    str(root/'src/aerothon_perception/perception_redzone'), str(root/'src/aerothon_perception/perception_banner')]
from perception_redzone.redzone_node import RedZoneNode
from mission_bt.mav_commander import Mav
variant = sys.argv[1]
assert variant in ('before', 'after', 'regressions')
label = sys.argv[2] if len(sys.argv) > 2 else '20261007'
out = root/('logs/reliability_provisional_red_entry_'+variant+'_'+label)
out.mkdir(exist_ok=False)
if variant != 'before':
    from provisional_red_entry_candidate_20261007 import install
    install(RedZoneNode, Mav, out/'source_override')
tests = [str(Path(__file__).with_name('test_provisional_red_entry_20261007.py'))]
if variant == 'regressions':
    tests += [str(root/'sim'/name) for name in ('test_redzone_georef.py', 'test_perception_corruption.py', 'test_geofence.py', 'test_detector_timing.py')]
code = pytest.main(['-q', *tests])
(out/'report.json').write_text(json.dumps(dict(exit_code=int(code), variant=variant, production_modified=False,
    rendered_qualified=False, scope='Controlled camera fixture and actual mission consumer; no simulator decision inputs'))+'\n')
raise SystemExit(code)
