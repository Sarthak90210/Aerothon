"""Run real connected-path logic from the isolated candidate."""
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[2]
snapshot = root/'.scratch/tracking_margin_candidate_20261007'
sys.path[:0] = [str(snapshot/'src/aerothon_avoidance/avoidance'), str(root/'sim')]
from avoidance import velocity_controller
assert Path(velocity_controller.__file__).resolve().is_relative_to(snapshot.resolve())
import pytest
raise SystemExit(pytest.main(['-q', str(Path(__file__).with_name('test_tracking_margin_contract_20261007.py'))]))
