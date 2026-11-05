"""Run the actual controller fault path before and after the isolated repair."""
import sys
from pathlib import Path
import pytest

root = Path(__file__).resolve().parents[2]
variant = sys.argv[1]
assert variant in ('before', 'after')
snapshot = root/'.scratch/lidar_fault_continuity_candidate_20261007'
sys.path.insert(0, str(snapshot/'src/aerothon_avoidance/avoidance'))
from avoidance import velocity_controller
assert Path(velocity_controller.__file__).resolve().is_relative_to(snapshot.resolve())
if variant == 'before':
    source = (root/'logs/reliability_lidar_fault_continuity_source_20261007/velocity_controller.before.py').read_text()
    namespace = dict(velocity_controller.__dict__)
    exec(compile(source, '<archived controller before repair>', 'exec'), namespace)
    velocity_controller.VelocityController._publish = namespace['VelocityController']._publish
raise SystemExit(pytest.main(['-q', str(Path(__file__).with_name('test_lidar_fault_observer_continuity_20261007.py'))]))
