"""Verify that targeted trials share the current drone code and actual archives."""
import hashlib
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
paths = [Path(p) for p in sys.argv[1:]] if len(sys.argv) == 3 else [root/'logs'/name for name in (
    'reliability_render_my_world_s20261003_retry4_20261006',
    'reliability_render_my_world_s1001_20261006')]
manifests = [json.loads((p/'source_manifest.json').read_text()) for p in paths]
assert manifests[0] == manifests[1], 'Targeted source manifests differ'
checked = 0
for name, expected in manifests[0].items():
    if name.startswith('src/'):
        assert hashlib.sha256((root/name).read_bytes()).hexdigest() == expected, name
        checked += 1
for path in paths:
    assert json.loads((path/'summary.json').read_text())['acceptance_pass']
    verification = json.loads((path/'source_archive_verification.json').read_text())
    assert verification['archive_verified']
    assert hashlib.sha256((path/verification['archive']).read_bytes()).hexdigest() == verification['archive_sha256']
print(json.dumps(dict(targeted_trials=2, acceptance_pass=True,
                      current_drone_source_files_verified=checked,
                      exact_recorded_source_archives_verified=True)))
