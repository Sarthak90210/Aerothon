"""Archive the source of the closed focus without changing its failed verdict."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'logs/reliability_corrected_headless_focus_20261007'
RUN = OUT / 'my_world_calm_s1'
FROZEN = ROOT / 'logs/reliability_observation_and_capture_qualification_20261007/source_manifest.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    result = json.loads((OUT / 'summary.json').read_text())
    assert result['result'] == 'FAILED' and result['navigation_pass'] is False
    recorded = json.loads((RUN / 'source_manifest.json').read_text())
    frozen = json.loads(FROZEN.read_text())
    assert all(frozen.get(name) == value for name, value in recorded.items())
    archive = OUT / 'frozen_source.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as stream:
        for name, expected in sorted(frozen.items()):
            data = (ROOT / name).read_bytes()
            assert digest(data) == expected, name
            stream.writestr(name, data)
        stream.writestr('source_manifest.json', json.dumps(frozen, indent=2) + '\n')
    with zipfile.ZipFile(archive) as stream:
        assert all(digest(stream.read(name)) == value for name, value in frozen.items())
    audit = dict(
        source_files=len(frozen), recorded_source_files=len(recorded),
        archived_source_sha256=digest(archive.read_bytes()),
        source_manifest_matches_recorded_run=True, archive_verified=True,
        run_verdict=result, rendered_perception_qualified=False,
        motor_delivery_qualified=False,
        limitation='Object-generated camera observations; no rendered frames or motor telemetry',
    )
    (OUT / 'source_archive_review.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
