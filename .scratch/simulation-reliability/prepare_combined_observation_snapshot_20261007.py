"""Combine verified observation changes in a new isolated source archive."""
import hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
buffer_archive=root/'logs/reliability_buffered_stamped_fixture_preparation_20261007/rejected_regression_source.zip'
gate_archive=root/'logs/reliability_gate_pause_navigation_source_20261007/frozen_source.zip'
assert hashlib.sha256(buffer_archive.read_bytes()).hexdigest()=='8916a3ededd80cda7bd82f159e048ba62948cd2a6a3cbc18e0ab80930fd7c5af'
assert hashlib.sha256(gate_archive.read_bytes()).hexdigest()=='bff95f7354418d3ba4b8ce3f2d22e29f991cff945ad9a20b0e53b30e8530cec0'
buffer_review=json.loads((root/'logs/reliability_buffered_scan_navigation_seed3_20261007/closed_trial_review.json').read_text())
assert buffer_review['navigation_pass'] and buffer_review['sampling_reserve_pass'] and buffer_review['source_unchanged']
gate_report=json.loads((root/'logs/reliability_gate_pause_navigation_seed5_20261007/report.json').read_text())
assert gate_report['source_unchanged'] and gate_report['forecast_recording_closed']
assert gate_report['result']['navigation_failures']==['flight within 900 s']
snapshot=root/'.scratch/combined_observation_motion_candidate_20261007';snapshot.mkdir(exist_ok=False)
with zipfile.ZipFile(buffer_archive) as source:
    frozen=json.loads(source.read('source_manifest.json'))
    for name,sha in frozen.items():
        data=source.read(name);assert hashlib.sha256(data).hexdigest()==sha
        path=(snapshot/name).resolve();assert path.is_relative_to(snapshot.resolve())
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
gate_name='src/aerothon_mission/mission_bt/mission_bt/gate_braking_candidate.py'
with zipfile.ZipFile(gate_archive) as source:
    manifest=json.loads(source.read('source_manifest.json'));data=source.read(gate_name)
    assert hashlib.sha256(data).hexdigest()==manifest[gate_name]
    (snapshot/gate_name).write_bytes(data)
assets=json.loads((root/'.scratch/buffered_scan_motion_candidate_20261007/candidate_provenance.json').read_text())['asset_sha256']
for name,sha in assets.items():
    data=(root/'.scratch/buffered_scan_motion_candidate_20261007'/name).read_bytes()
    assert hashlib.sha256(data).hexdigest()==sha
    path=(snapshot/name).resolve();assert path.is_relative_to(snapshot.resolve())
    if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
    else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
frozen={name:hashlib.sha256((snapshot/name).read_bytes()).hexdigest() for name in frozen}
out=root/'logs/reliability_combined_observation_navigation_source_20261007';out.mkdir(exist_ok=False)
with zipfile.ZipFile(out/'frozen_source.zip','x',zipfile.ZIP_DEFLATED) as source:
    source.writestr('source_manifest.json',json.dumps(frozen,indent=2)+'\n')
    for name in sorted(frozen):source.writestr(name,(snapshot/name).read_bytes())
with zipfile.ZipFile(out/'frozen_source.zip') as source:
    assert all(hashlib.sha256(source.read(name)).hexdigest()==sha for name,sha in frozen.items())
provenance=dict(buffer_archive_sha256=hashlib.sha256(buffer_archive.read_bytes()).hexdigest(),
    gate_archive_sha256=hashlib.sha256(gate_archive.read_bytes()).hexdigest(),asset_sha256=assets,
    source_archive_sha256=hashlib.sha256((out/'frozen_source.zip').read_bytes()).hexdigest(),
    source_archive_verified=True,source_files=len(frozen),physical_fixture_changed=False,
    clearance_limits_changed=False,production_adopted=False,
    source_changes=['buffer paired lidar captures','bounded gate observation pause'])
(out/'candidate_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
(snapshot/'candidate_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print(json.dumps({k:v for k,v in provenance.items() if k!='asset_sha256'}))
