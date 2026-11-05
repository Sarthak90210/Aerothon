"""Run existing actuator and traversal regressions with capture pairing installed."""
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/paired_scan_motion_candidate_20261007'
sys.path.insert(0,str(snapshot/'src/aerothon_avoidance/avoidance'))
from avoidance import velocity_controller,paired_scan_pose
assert Path(velocity_controller.__file__).resolve().is_relative_to(snapshot.resolve())
original=velocity_controller.VelocityController.__init__
def initialize(node,*args,**kwargs):
    original(node,*args,**kwargs);paired_scan_pose.install(node)
velocity_controller.VelocityController.__init__=initialize
print(json.dumps(dict(decision_import=velocity_controller.__file__,registration_import=paired_scan_pose.__file__)),flush=True)
import pytest
raise SystemExit(pytest.main(['-q',str(root/'sim/test_slalom_traverse.py'),
    str(root/'sim/test_velocity_command_delay.py'),str(root/'sim/test_fcu_navigation_velocity.py'),
    str(root/'sim/test_fcu_velocity_sample_alignment.py')]))
