"""Check a pruned source enumeration against the active frozen manifest."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'sim'))
from campaign_record import source_manifest


def fast_manifest():
    source_manifest.cache_clear()
    data = source_manifest(ROOT)
    for directory in ('src', 'scripts', 'sim'):
        for path, dirs, files in os.walk(ROOT / directory):
            dirs[:] = [name for name in dirs if name not in (
                'node_modules', 'dist', 'build', '__pycache__')]
            for name in files:
                candidate = Path(path) / name
                if candidate.suffix in ('.xacro', '.urdf', '.png', '.txt', '.glb'):
                    data[candidate.relative_to(ROOT).as_posix()] = hashlib.sha256(
                        candidate.read_bytes()).hexdigest()
    for name in ('capture_runtime_configuration.py', 'audit_decision_inputs.py',
                 'grade_focused_return.py', 'grade_focused_delivery.py'):
        candidate = Path(__file__).with_name(name)
        data[candidate.relative_to(ROOT).as_posix()] = hashlib.sha256(
            candidate.read_bytes()).hexdigest()
    candidate = ROOT / 'logs/delivery_profile_20261005.json'
    data[candidate.relative_to(ROOT).as_posix()] = hashlib.sha256(
        candidate.read_bytes()).hexdigest()
    return data


if __name__ == '__main__':
    expected = json.loads((ROOT / 'logs/reliability_observation_and_capture_qualification_20261007/source_manifest.json').read_text())
    started = time.monotonic()
    actual = fast_manifest()
    report = dict(matches_active_frozen_manifest=actual == expected,
                  source_files=len(actual), elapsed_wall_s=time.monotonic()-started,
                  changed={name: (expected.get(name), actual.get(name))
                           for name in actual.keys() | expected.keys()
                           if actual.get(name) != expected.get(name)},
                  limitation='Future coordinator optimization; active coordinator is unchanged')
    print(json.dumps(report, indent=2))
    (Path(__file__).with_name('fast_manifest_review_20261007.json')).write_text(
        json.dumps(report, indent=2) + '\n')
    raise SystemExit(0 if report['matches_active_frozen_manifest'] else 1)
