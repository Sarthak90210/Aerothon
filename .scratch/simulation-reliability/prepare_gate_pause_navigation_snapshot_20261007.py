"""Create and archive a gate-only candidate, preserving the failed field trial source."""
import hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
qualified=root/'logs/reliability_paired_scan_navigation_s5_assets_20261007'
archive=qualified/'frozen_source.zip';review=json.loads((qualified/'source_archive_review.json').read_text())
assert review['archive_verified'] and hashlib.sha256(archive.read_bytes()).hexdigest()==review['archive_sha256']
contract=json.loads((root/'logs/reliability_gate_observation_pause_contract_20261007/report.json').read_text())
assert contract['passed'] and len(contract['checks'])==5
snapshot=root/'.scratch/gate_pause_motion_candidate_20261007';snapshot.mkdir(exist_ok=False)
with zipfile.ZipFile(archive) as source:
    frozen=json.loads(source.read('source_manifest.json'))
    for name,sha in frozen.items():
        data=source.read(name);assert hashlib.sha256(data).hexdigest()==sha
        path=(snapshot/name).resolve();assert path.is_relative_to(snapshot.resolve())
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
assets_provenance=json.loads((qualified/'candidate_provenance.json').read_text())
assets=assets_provenance['missing_assets_recovered_from_verified_archive']
asset_archive=root/'logs/reliability_corrected_headless_focus_20261007/frozen_source.zip'
assert hashlib.sha256(asset_archive.read_bytes()).hexdigest()==assets_provenance['asset_archive_sha256']
with zipfile.ZipFile(asset_archive) as source:
    for name,sha in assets.items():
        data=source.read(name);assert hashlib.sha256(data).hexdigest()==sha
        path=(snapshot/name).resolve();assert path.is_relative_to(snapshot.resolve())
        if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
gate=snapshot/'src/aerothon_mission/mission_bt/mission_bt/gate_braking_candidate.py'
text=gate.read_text();original_sha=hashlib.sha256(gate.read_bytes()).hexdigest()
old='        self._started = self._now()'
assert text.count(old)==1
text=text.replace(old,old+'\n        self._observation_wait_started = None')
old="""        if motion is None:
            self._hold_position()
            return self._fail('fresh pose, velocity and lidar capture times required')
        speed, velocity_stamp = motion"""
new="""        if motion is None:
            self._hold_position()
            if self._observation_wait_started is None:
                self._observation_wait_started = now
            self._settle_first = self._settle_last = None
            self._settle_count = 0
            elapsed = now-self._observation_wait_started
            if 0 <= elapsed <= 1.0:
                self.feedback_message = 'holding measured gate position while awaiting fresh captures'
                return RUNNING
            return self._fail('fresh observations did not recover during bounded gate hold')
        self._observation_wait_started = None
        speed, velocity_stamp = motion"""
assert text.count(old)==1;text=text.replace(old,new);gate.write_text(text)
manifest={name:hashlib.sha256((snapshot/name).read_bytes()).hexdigest() for name in frozen}
out=root/'logs/reliability_gate_pause_navigation_source_20261007';out.mkdir(exist_ok=False)
with zipfile.ZipFile(out/'frozen_source.zip','x',zipfile.ZIP_DEFLATED) as source:
    for name in sorted(manifest):source.writestr(name,(snapshot/name).read_bytes())
    source.writestr('source_manifest.json',json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(out/'frozen_source.zip') as source:
    assert all(hashlib.sha256(source.read(name)).hexdigest()==sha for name,sha in manifest.items())
provenance=dict(base_archive_sha256=review['archive_sha256'],original_gate_sha256=original_sha,
    gate_sha256=hashlib.sha256(gate.read_bytes()).hexdigest(),asset_sha256=assets,
    source_archive_sha256=hashlib.sha256((out/'frozen_source.zip').read_bytes()).hexdigest(),
    source_files=len(manifest),source_archive_verified=True,physical_fixture_changed=False,
    source_changes=['bounded one-second hold on missing gate observations; distinct dwell reset'],
    clearance_limits_changed=False,production_adopted=False,buffered_scan_change_included=False)
(out/'candidate_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
(snapshot/'candidate_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print(json.dumps({k:v for k,v in provenance.items() if k!='asset_sha256'}))
