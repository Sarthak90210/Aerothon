"""Extract and verify the exact qualified source for an isolated baseline matrix."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
FIRST = ROOT / 'logs/reliability_render_my_world_s20261003_handover_guard_20261006'
SECOND = ROOT / 'logs/reliability_render_my_world_s1001_handover_guard_20261006'
DEST = ROOT / '.scratch/qualified_navigation_baseline_20261006'


def read(path):
    return json.loads(path.read_text())


pair = read(ROOT / 'logs/reliability_standard_pair_handover_guard_20261006.json')
assert pair['both_full_acceptances_passed'] is True
assert pair['full_offline_suite_exit_code'] == 0 and pair['source_unchanged'] is True
manifests = [read(run / 'source_manifest.json') for run in (FIRST, SECOND)]
assert manifests[0] == manifests[1], 'Qualified sources differ'
archives = [read(run / 'source_archive_verification.json') for run in (FIRST, SECOND)]
for run, archive in zip((FIRST, SECOND), archives):
    assert archive['archive_verified'] is True
    assert hashlib.sha256((run / archive['archive']).read_bytes()).hexdigest() == archive['archive_sha256']
for name, expected in manifests[0].items():
    path = Path(name)
    if not path.is_absolute():
        path = ROOT / path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'Current source changed: ' + name
DEST.mkdir(exist_ok=False)
with zipfile.ZipFile(FIRST / archives[0]['archive']) as archive:
    frozen = json.loads(archive.read('archive_manifest.json'))
    for relative, expected in frozen.items():
        target = (DEST / relative).resolve()
        assert target.is_relative_to(DEST.resolve()), 'Unsafe archive member'
        data = archive.read('source/' + relative)
        assert hashlib.sha256(data).hexdigest() == expected, 'Archived source changed: ' + relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == expected
for name, expected in manifests[0].items():
    if name.startswith('src/'):
        assert hashlib.sha256((DEST / name).read_bytes()).hexdigest() == expected
report = dict(source='exact standard-pair qualified archive', snapshot=str(DEST),
    source_entries_verified=len(frozen), standard_seeds=[20261003, 1001],
    archive=archives[0], qualification_pair=pair,
    limitations=['Current-source coupled narrow-corridor gust/delay tests fail.',
                 'This snapshot campaign cannot qualify a later producer repair.',
                 'Headless navigation cannot qualify rendered perception or motor delivery.'])
(DEST / 'snapshot_verification.json').write_text(json.dumps(report, indent=2) + '\n')
(DEST / 'recorded_source.zip').write_bytes((FIRST / archives[0]['archive']).read_bytes())
print(json.dumps(report, indent=2))
