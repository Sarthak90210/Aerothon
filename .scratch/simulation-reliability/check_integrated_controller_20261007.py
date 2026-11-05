"""Run publication contracts against the exact staged production controller."""
import importlib.util
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[2]
staged = root/'.scratch/controller_integration_20261007/src/aerothon_avoidance/avoidance/avoidance'
sys.path.insert(0, str(root/'sim'))
spec = importlib.util.spec_from_file_location('avoidance',
    root/'src/aerothon_avoidance/avoidance/avoidance/__init__.py',
    submodule_search_locations=[str(staged), str(root/'src/aerothon_avoidance/avoidance/avoidance')])
package = importlib.util.module_from_spec(spec)
sys.modules['avoidance'] = package
spec.loader.exec_module(package)
import pytest
raise SystemExit(pytest.main(['-q',
    str(root/'.scratch/simulation-reliability/test_command_computation_deadline_20261007.py'),
    str(root/'sim/test_corridor_clearance_contract.py'),
    str(root/'sim/test_velocity_command_delay.py'),
    str(root/'sim/test_fcu_velocity_sample_alignment.py')]))
