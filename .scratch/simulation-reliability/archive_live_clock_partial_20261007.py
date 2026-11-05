"""Archive the stopped faulty candidate before its one-line correction."""
import hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/braked_navigation_candidate_20261007'
out=root/'logs/reliability_live_clock_navigation_candidate_20261007'
manifest=json.loads((out/'my_world_calm_s1/source_manifest.json').read_text())
sha=lambda data:hashlib.sha256(data).hexdigest()
with zipfile.ZipFile(out/'frozen_source.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
    for name,expected in manifest.items():
        data=(snapshot/name).read_bytes();assert sha(data)==expected,name
        archive.writestr(name,data)
    archive.writestr('source_manifest.json',json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(out/'frozen_source.zip') as archive:
    assert all(sha(archive.read(name))==expected for name,expected in manifest.items())
closure=dict(state='STOPPED_CONTROLLER_EXCEPTION',qualification_pass=False,
    reason='Capture-age forecast referenced a locally assigned delay before initialization',
    source_archive_verified=True,source_files=len(manifest),
    archive_sha256=sha((out/'frozen_source.zip').read_bytes()),
    simulator_physics_changed=False,complete_camera_or_disarm_claim=False)
(out/'partial_trial.json').write_text(json.dumps(closure,indent=2)+'\n')
print(json.dumps(closure))
