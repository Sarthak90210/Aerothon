"""Run existing physical-loop tests against the actual isolated candidate."""
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/braked_navigation_candidate_20261007'
sys.path.insert(0,str(snapshot/'src/aerothon_avoidance/avoidance'))
from avoidance import velocity_controller
assert Path(velocity_controller.__file__).resolve().is_relative_to(snapshot.resolve())
print(json.dumps(dict(decision_import=str(Path(velocity_controller.__file__).resolve()))),flush=True)
import pytest
raise SystemExit(pytest.main(['-q',str(root/'sim/test_slalom_traverse.py'),
    str(root/'sim/test_velocity_command_delay.py'),
    str(root/'sim/test_fcu_navigation_velocity.py'),
    str(root/'sim/test_fcu_velocity_sample_alignment.py')]))
