"""Freeze measured-arrival braking and contact grading with the camera candidates."""
import hashlib,json,shutil,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
from campaign_record import source_manifest
snapshot=root/'.scratch/arrival_anchor_framing_candidate_20261007'
evidence=root/'logs/reliability_arrival_anchor_framing_source_20261007'
snapshot.mkdir(exist_ok=False);evidence.mkdir(exist_ok=False)
manifest={name.replace('\\','/'):sha for name,sha in source_manifest(root).items()}
for name,sha in manifest.items():
    src=root/name;dst=snapshot/name;dst.parent.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(src.read_bytes()).hexdigest()==sha,name
    shutil.copy2(src,dst)
for module in ('fine_return_framing','clipped_bearing_return'):
    name=f'sim/{module}_candidate.py'
    shutil.copy2(root/f'.scratch/simulation-reliability/{module}_candidate_20261007.py',snapshot/name)
    manifest[name]=hashlib.sha256((snapshot/name).read_bytes()).hexdigest()
name='sim/navigation_mission.py';path=snapshot/name
source=path.read_text(encoding='utf-8');needle='    mission_tree.main()';assert source.count(needle)==1
source=source.replace(needle,"    from sim.fine_return_framing_candidate import FineReturnFraming\n    mission_tree.AlignToBanner=FineReturnFraming\n    mission_tree.STATE_NAMES['FineReturnFraming']='BANNER_ALIGN'\n    from sim.clipped_bearing_return_candidate import FramedReturnBanner\n    mission_tree.FindReturnBanner=FramedReturnBanner\n    mission_tree.STATE_NAMES['FramedReturnBanner']='RETURN_GATE_SEARCH'\n"+needle)
path.write_bytes(source.encode());manifest[name]=hashlib.sha256(path.read_bytes()).hexdigest()
(snapshot/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
with zipfile.ZipFile(evidence/'frozen_source.zip','x',zipfile.ZIP_DEFLATED) as archive:
    for name in manifest:archive.write(snapshot/name,name)
    archive.write(snapshot/'source_manifest.json','source_manifest.json')
provenance=dict(scope='Measured-arrival gate braking, independent contact grading and isolated camera framing; object-level navigation only',
    files=len(manifest),archive_sha256=hashlib.sha256((evidence/'frozen_source.zip').read_bytes()).hexdigest(),accepted_source=False)
(evidence/'provenance.json').write_text(json.dumps(provenance,indent=2))
launcher=root/'.scratch/simulation-reliability/run_arrival_anchor_framing_field_20261007.py'
source=(root/'.scratch/simulation-reliability/run_clipped_bearing_framing_field_20261007.py').read_text().replace('clipped_bearing_framing','arrival_anchor_framing')
with launcher.open('x',newline='\n') as stream:stream.write(source)
print(json.dumps(provenance))
