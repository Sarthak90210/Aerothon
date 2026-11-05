"""Actual publication method, archived before and isolated after repair."""
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[2]
variant = sys.argv[1]
assert variant in ('before','after')
snapshot = root/'.scratch/command_deadline_candidate_20261007'
sys.path[:0] = [str(snapshot/'src/aerothon_avoidance/avoidance'),str(root/'sim')]
from avoidance import velocity_controller
assert Path(velocity_controller.__file__).resolve().is_relative_to(snapshot.resolve())
if variant == 'before':
    source = (root/'logs/reliability_command_deadline_source_20261007/controller.before.py').read_text()
    namespace = dict(velocity_controller.__dict__)
    exec(compile(source,'<archived before deadline repair>','exec'),namespace)
    velocity_controller.VelocityController._publish = namespace['VelocityController']._publish
import pytest
raise SystemExit(pytest.main(['-q',str(Path(__file__).with_name('test_command_computation_deadline_20261007.py'))]))
