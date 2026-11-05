"""Run unchanged controller assertions against properly stamped observations."""
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/tracking_margin_candidate_20261007'
fixtures=root/'.scratch/buffered_stamped_regression_fixtures_20261007'
sys.path[:0]=[str(snapshot/'src/aerothon_avoidance/avoidance'),str(fixtures)]
from avoidance import velocity_controller,buffered_scan_pose
assert Path(velocity_controller.__file__).resolve().is_relative_to(snapshot.resolve())
original=velocity_controller.VelocityController.__init__
def initialize(node,*args,**kwargs):
    original(node,*args,**kwargs);buffered_scan_pose.install(node)
velocity_controller.VelocityController.__init__=initialize
print(json.dumps(dict(decision_import=velocity_controller.__file__,registration_import=buffered_scan_pose.__file__,fixture_directory=str(fixtures))),flush=True)
import pytest
raise SystemExit(pytest.main(['-q',*[str(fixtures/name) for name in (
    'test_slalom_traverse.py','test_velocity_command_delay.py','test_fcu_navigation_velocity.py',
    'test_fcu_velocity_sample_alignment.py')]]))
