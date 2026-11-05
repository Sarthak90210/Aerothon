"""Add the camera-only clipped-ray retry to the already archived candidate."""
import hashlib,json,shutil,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
base=root/'.scratch/scoped_fine_framing_candidate_20261007'
snapshot=root/'.scratch/clipped_bearing_framing_candidate_20261007'
evidence=root/'logs/reliability_clipped_bearing_framing_source_20261007'
snapshot.mkdir(exist_ok=False);evidence.mkdir(exist_ok=False)
manifest=json.loads((base/'source_manifest.json').read_text())
for name,sha in manifest.items():
    assert hashlib.sha256((base/name).read_bytes()).hexdigest()==sha,name
    target=snapshot/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(base/name,target)
name='sim/clipped_bearing_return_candidate.py'
shutil.copy2(root/'.scratch/simulation-reliability/clipped_bearing_return_candidate_20261007.py',snapshot/name)
manifest[name]=hashlib.sha256((snapshot/name).read_bytes()).hexdigest()
name='sim/navigation_mission.py';path=snapshot/name
source=path.read_text(encoding='utf-8');needle='    mission_tree.main()';assert source.count(needle)==1
source=source.replace(needle,"    from sim.clipped_bearing_return_candidate import FramedReturnBanner\n    mission_tree.FindReturnBanner=FramedReturnBanner\n    mission_tree.STATE_NAMES['FramedReturnBanner']='RETURN_GATE_SEARCH'\n"+needle)
path.write_bytes(source.encode());manifest[name]=hashlib.sha256(path.read_bytes()).hexdigest()
(snapshot/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
with zipfile.ZipFile(evidence/'frozen_source.zip','x',zipfile.ZIP_DEFLATED) as archive:
    for name in manifest:archive.write(snapshot/name,name)
    archive.write(snapshot/'source_manifest.json','source_manifest.json')
provenance=dict(scope='Scoped escape and bounded fine framing plus camera-only clipped-bearing retry; object-level navigation only',
    files=len(manifest),archive_sha256=hashlib.sha256((evidence/'frozen_source.zip').read_bytes()).hexdigest(),accepted_source=False)
(evidence/'provenance.json').write_text(json.dumps(provenance,indent=2))
launcher=root/'.scratch/simulation-reliability/run_clipped_bearing_framing_field_20261007.py'
source=(root/'.scratch/simulation-reliability/run_scoped_fine_framing_field_20261007.py').read_text().replace('scoped_fine_framing','clipped_bearing_framing')
with launcher.open('x',newline='\n') as stream:stream.write(source)
print(json.dumps(provenance))
