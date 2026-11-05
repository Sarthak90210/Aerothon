"""Isolate one observer repair while rendered production source remains frozen."""
import hashlib
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
base = root/'logs/reliability_combined_observation_navigation_source_20261007'
archive = base/'frozen_source.zip'
provenance = json.loads((base/'candidate_provenance.json').read_text())
assert hashlib.sha256(archive.read_bytes()).hexdigest() == provenance['source_archive_sha256']
snapshot = root/'.scratch/lidar_fault_continuity_candidate_20261007'
out = root/'logs/reliability_lidar_fault_continuity_source_20261007'
snapshot.mkdir(exist_ok=False)
out.mkdir(exist_ok=False)
with zipfile.ZipFile(archive) as source:
    manifest = json.loads(source.read('source_manifest.json'))
    for name, sha in manifest.items():
        data = source.read(name)
        assert hashlib.sha256(data).hexdigest() == sha
        path = (snapshot/name).resolve()
        assert path.is_relative_to(snapshot.resolve())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
for name, sha in provenance['asset_sha256'].items():
    data = (root/'.scratch/combined_observation_motion_candidate_20261007'/name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == sha
    path = (snapshot/name).resolve()
    assert path.is_relative_to(snapshot.resolve())
    if path.exists():
        assert path.read_bytes() == data
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
name = 'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
controller = snapshot/name
before = controller.read_text()
(out/'velocity_controller.before.py').write_text(before)
old = '''            self._reset_drift()
            self._command_history=pending'''
new = '''            # A lidar fault prohibits motion, but it does not invalidate
            # independently fresh FCU motion samples. Erasing the observer
            # here makes the next scan treat measured wind as a new handover.
            flight_fresh = (self._pose_t is not None and
                self._now()-self._pose_t <= float(self._g('stale_scan_s')) and
                not self._velocity_fault and self._velocity_fresh())
            if flight_fresh:
                self._compensated(0.0,0.0)
            else:
                self._reset_drift()
            self._command_history=pending'''
assert before.count(old) == 1
controller.write_text(before.replace(old, new))
(out/'velocity_controller.candidate.py').write_bytes(controller.read_bytes())
manifest = {name: hashlib.sha256((snapshot/name).read_bytes()).hexdigest() for name in manifest}
with zipfile.ZipFile(out/'frozen_source.zip', 'x', zipfile.ZIP_DEFLATED) as target:
    target.writestr('source_manifest.json', json.dumps(manifest, indent=2)+'\n')
    for name in sorted(manifest):
        target.writestr(name, (snapshot/name).read_bytes())
with zipfile.ZipFile(out/'frozen_source.zip') as target:
    assert all(hashlib.sha256(target.read(name)).hexdigest() == sha for name, sha in manifest.items())
record = dict(source_archive_verified=True, source_archive_sha256=hashlib.sha256((out/'frozen_source.zip').read_bytes()).hexdigest(),
              asset_sha256=provenance['asset_sha256'], source_files=len(manifest), production_adopted=False,
              physical_fixture_changed=False, clearance_limits_changed=False,
              source_changes=['retain observer continuity during lidar-only stop with fresh FCU observations'])
(out/'candidate_provenance.json').write_text(json.dumps(record, indent=2)+'\n')
(snapshot/'candidate_provenance.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k != 'asset_sha256'}))
