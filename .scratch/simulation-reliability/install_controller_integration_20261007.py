"""Install reviewed changes after actual disarm, retaining prior source bytes."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
run = root/'logs/reliability_render_rb_rotated_s20261003_early_red_clipped_bearing_fixture_clock_20261007'
summary = json.loads((run/'summary.json').read_text())
assert summary['final_armed'] is False and summary['acceptance_pass'] is False
assert '27 passed' in (root/'logs/reliability_controller_integration_contract_frozen_fixture_20261007.log').read_text()
assert '4 passed' in (root/'logs/reliability_controller_integration_startup_20261007.log').read_text()
review = root/'logs/reliability_controller_integration_review_20261007'
review.mkdir(exist_ok=False)
staged = root/'.scratch/controller_integration_20261007/src/aerothon_avoidance/avoidance/avoidance'
manifest = json.loads((root/'.scratch/controller_integration_20261007/integration_manifest.json').read_text())
changes = []
for name, metadata in manifest.items():
    data = (staged/name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == metadata['staged_sha256']
    target = root/'src/aerothon_avoidance/avoidance/avoidance'/name
    old = target.read_bytes() if target.exists() else None
    if old is not None:
        (review/(name+'.before')).write_bytes(old)
    (review/(name+'.installed')).write_bytes(data)
    target.write_bytes(data)
    changes.append(dict(file=target.relative_to(root).as_posix(), before_sha256=hashlib.sha256(old).hexdigest() if old else None,
                        after_sha256=hashlib.sha256(data).hexdigest()))
test = root/'sim/test_command_computation_deadline.py'
assert not test.exists()
test.write_bytes((root/'.scratch/simulation-reliability/test_command_computation_deadline_20261007.py').read_bytes())
(review/'installation.json').write_text(json.dumps(dict(changes=changes, rendered_recording_closed=True,
    scope='Installed scheduling/controller integration; current rendered and campaign qualification pending'), indent=2)+'\n')
print(json.dumps(dict(installed=len(changes), qualification_pass=False)))
