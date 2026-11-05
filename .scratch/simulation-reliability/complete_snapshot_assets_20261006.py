"""Freeze omitted non-code assets without changing any archived source bytes."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
snapshot = root / '.scratch/qualified_navigation_baseline_20261006'
directory = root / 'src/aerothon_sim/sim_gazebo/materials'
manifest = {}
for source in sorted(directory.rglob('*')):
    if not source.is_file():
        continue
    relative = source.relative_to(root)
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    target = snapshot / relative
    if target.exists():
        assert target.read_bytes() == data, 'Refuse to overwrite archived asset'
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as output:
            output.write(data)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
    manifest[relative.as_posix()] = digest
report = dict(provenance='Current workspace non-code materials frozen at campaign setup',
    earlier_qualified_archive_contains_these_assets=False,
    source_code_changed=False, sha256=manifest)
with (snapshot / 'additional_assets_manifest.json').open('x') as output:
    output.write(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
