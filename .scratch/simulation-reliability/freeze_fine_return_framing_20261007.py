"""Freeze the existing certified search repair with one isolated camera handoff."""
import hashlib,json,shutil,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/monotonic_search_escape_candidate_20261007'
out=root/'.scratch/fine_return_framing_candidate_20261007';out.mkdir(exist_ok=False)
evidence=root/'logs/reliability_fine_return_framing_source_20261007';evidence.mkdir(exist_ok=False)
manifest=json.loads((base/'source_manifest.json').read_text())
for name,sha in manifest.items():
 p=base/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==sha,name
 target=out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
name='sim/fine_return_framing_candidate.py';p=out/name
shutil.copy2(root/'.scratch/simulation-reliability/fine_return_framing_candidate_20261007.py',p)
manifest[name]=hashlib.sha256(p.read_bytes()).hexdigest()
name='sim/navigation_mission.py';p=out/name;s=p.read_text(encoding='utf-8')
needle='    mission_tree.main()';assert s.count(needle)==1
s=s.replace(needle,"    from sim.fine_return_framing_candidate import FineReturnFraming\n    mission_tree.AlignToBanner=FineReturnFraming\n    mission_tree.STATE_NAMES['FineReturnFraming']='BANNER_ALIGN'\n"+needle)
p.write_bytes(s.encode());manifest[name]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
with zipfile.ZipFile(evidence/'frozen_source.zip','x',zipfile.ZIP_DEFLATED) as z:
 for name in manifest:z.write(out/name,name)
 z.write(out/'source_manifest.json','source_manifest.json')
review=dict(scope='Isolated fine return yaw sweep and high-altitude look restoration plus monotonic search escapes; object-level navigation only; no production adoption',files=len(manifest),archive_sha256=hashlib.sha256((evidence/'frozen_source.zip').read_bytes()).hexdigest(),accepted_source=False)
(evidence/'provenance.json').write_text(json.dumps(review,indent=2));print(json.dumps(review))
p=root/'.scratch/simulation-reliability/run_monotonic_search_escape_field_20261007.py';s=p.read_text(encoding='utf-8').replace('monotonic_search_escape_candidate_20261007','fine_return_framing_candidate_20261007').replace('reliability_monotonic_search_escape_source_20261007','reliability_fine_return_framing_source_20261007').replace('reliability_monotonic_search_escape_field_s','reliability_fine_return_framing_field_s')
(root/'.scratch/simulation-reliability/run_fine_return_framing_field_20261007.py').write_bytes(s.encode())
