"""Freeze the scoped escape repair with the separately tested framing retry."""
import hashlib,json,shutil,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
from campaign_record import source_manifest
snapshot=root/'.scratch/scoped_fine_framing_candidate_20261007'
evidence=root/'logs/reliability_scoped_fine_framing_source_20261007'
snapshot.mkdir(exist_ok=False);evidence.mkdir(exist_ok=False)
manifest={name.replace('\\','/'):sha for name,sha in source_manifest(root).items()}
for name,sha in manifest.items():
    src=root/name;dst=snapshot/name;dst.parent.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(src.read_bytes()).hexdigest()==sha
    shutil.copy2(src,dst)
name='sim/fine_return_framing_candidate.py'
shutil.copy2(root/'.scratch/simulation-reliability/fine_return_framing_candidate_20261007.py',snapshot/name)
manifest[name]=hashlib.sha256((snapshot/name).read_bytes()).hexdigest()
name='sim/navigation_mission.py';path=snapshot/name
source=path.read_text(encoding='utf-8');needle='    mission_tree.main()'
assert source.count(needle)==1
source=source.replace(needle,"    from sim.fine_return_framing_candidate import FineReturnFraming\n    mission_tree.AlignToBanner=FineReturnFraming\n    mission_tree.STATE_NAMES['FineReturnFraming']='BANNER_ALIGN'\n"+needle)
path.write_bytes(source.encode());manifest[name]=hashlib.sha256(path.read_bytes()).hexdigest()
(snapshot/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
with zipfile.ZipFile(evidence/'frozen_source.zip','x',zipfile.ZIP_DEFLATED) as archive:
    for name in manifest:archive.write(snapshot/name,name)
    archive.write(snapshot/'source_manifest.json','source_manifest.json')
provenance=dict(scope='Scoped containing-margin escape continuation and bounded fine return framing; object-level navigation only',
    files=len(manifest),archive_sha256=hashlib.sha256((evidence/'frozen_source.zip').read_bytes()).hexdigest(),accepted_source=False)
(evidence/'provenance.json').write_text(json.dumps(provenance,indent=2))
launcher=root/'.scratch/simulation-reliability/run_scoped_fine_framing_field_20261007.py'
source=(root/'.scratch/simulation-reliability/run_fine_return_framing_field_20261007.py').read_text().replace('fine_return_framing','scoped_fine_framing')
with launcher.open('x',newline='\n') as stream:stream.write(source)
print(json.dumps(provenance))
