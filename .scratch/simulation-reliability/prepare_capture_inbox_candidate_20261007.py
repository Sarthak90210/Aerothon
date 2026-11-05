"""Freeze an isolated capture-delivery candidate; preserve production runs."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

root = Path(__file__).resolve().parents[2]
base = root/'logs/reliability_command_deadline_source_20261007'
provenance = json.loads((base/'candidate_provenance.json').read_text())
archive = base/'frozen_source.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == provenance['source_archive_sha256']
snapshot = root/'.scratch/capture_inbox_candidate_20261007'
out = root/'logs/reliability_capture_inbox_source_20261007'
resume = '--resume-encoding-repair' in sys.argv
snapshot.mkdir(exist_ok=resume)
out.mkdir(exist_ok=resume)
if resume:
    assert not (out/'frozen_source.zip').exists()
    (out/'setup_retry.json').write_text(json.dumps(dict(
        original_error='Windows default text decoding rejected the UTF-8 controller',
        production_modified=False, flight_trials_started=False))+'\n', encoding='utf-8')
with zipfile.ZipFile(archive) as handle:
    manifest = json.loads(handle.read('source_manifest.json'))
    for name, sha in manifest.items():
        data = handle.read(name)
        assert hashlib.sha256(data).hexdigest() == sha
        target = (snapshot/name).resolve()
        assert target.is_relative_to(snapshot.resolve())
        if resume:
            assert hashlib.sha256(target.read_bytes()).hexdigest() == sha, name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
for name, sha in provenance['asset_sha256'].items():
    data = (root/'.scratch/command_deadline_candidate_20261007'/name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == sha
    target = (snapshot/name).resolve()
    assert target.is_relative_to(snapshot.resolve())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
name = 'src/aerothon_avoidance/avoidance/avoidance/capture_inbox.py'
data = Path(__file__).with_name('capture_inbox_candidate_20261007.py').read_bytes()
(snapshot/name).write_bytes(data)
manifest[name] = hashlib.sha256(data).hexdigest()
name = 'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
controller = snapshot/name
before = controller.read_text(encoding='utf-8')
after = before
old = '    clock_driver = IndependentRosClock(node)'
assert after.count(old) == 1
after = after.replace(old, old+'\n    from avoidance.capture_inbox import CaptureInbox\n    capture_driver = CaptureInbox(node)')
old = '        clock_driver.close()'
assert after.count(old) == 1
after = after.replace(old, '        capture_driver.close()\n'+old)
compile(after, name, 'exec')
controller.write_bytes(after.encode())
(out/'controller.before.py').write_text(before, encoding='utf-8')
(out/'controller.candidate.py').write_bytes(controller.read_bytes())
manifest = {name:hashlib.sha256((snapshot/name).read_bytes()).hexdigest() for name in manifest}
with zipfile.ZipFile(out/'frozen_source.zip', 'x', zipfile.ZIP_DEFLATED) as handle:
    handle.writestr('source_manifest.json', json.dumps(manifest, indent=2)+'\n')
    for name in sorted(manifest):
        handle.writestr(name, (snapshot/name).read_bytes())
with zipfile.ZipFile(out/'frozen_source.zip') as handle:
    assert all(hashlib.sha256(handle.read(name)).hexdigest() == sha for name,sha in manifest.items())
record = dict(provenance, source_files=len(manifest),
    source_archive_sha256=hashlib.sha256((out/'frozen_source.zip').read_bytes()).hexdigest(),
    source_changes=provenance['source_changes']+['receive onboard captures independently and apply one batch at control tick boundaries'],
    production_modified=False, flight_qualified=False,
    scope='Isolated scheduling candidate; disturbance or delivery qualification not inherited')
(out/'candidate_provenance.json').write_text(json.dumps(record, indent=2)+'\n')
(snapshot/'candidate_provenance.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps({key:value for key,value in record.items() if key!='asset_sha256'}))
