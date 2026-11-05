"""Reproduce old failure from frozen source without editing active source."""
import hashlib,json,sys,zipfile
from pathlib import Path
from unittest.mock import patch
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
import test_gate_motion_physics as fixture
archive=root/'logs/reliability_reduced_scope_v34_source_20261008/frozen_source.zip'
sha=hashlib.sha256(archive.read_bytes()).hexdigest()
assert sha=='34aad95e05f1fface7dd8b931892fb1d909d86e7004d2b7af554e2cc694dbd15'
with zipfile.ZipFile(archive) as z:source=z.read('src/aerothon_mission/mission_bt/mission_bt/gate_braking.py').decode()
namespace={'__name__':'frozen_v34_gate_braking'};exec(compile(source,'frozen_v34_gate_braking.py','exec'),namespace)
print(json.dumps(dict(source_archive_sha256=sha,scope='Frozen V34 actual gate leaf; evaluation-only captured error replay, regenerated wind/lidar; qualification false')),flush=True)
with patch.object(fixture,'BrakedGateAdvance',namespace['BrakedGateAdvance']):
    fixture.test_recorded_braking_retains_clearance_through_estimator_wander()
