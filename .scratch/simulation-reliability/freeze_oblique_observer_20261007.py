"""Freeze the existing certified search repair with one isolated camera handoff."""
import hashlib,json,shutil,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/certified_search_escape_candidate_20261007'
out=root/'.scratch/oblique_observer_candidate_20261007';out.mkdir(exist_ok=False)
evidence=root/'logs/reliability_oblique_observer_source_20261007';evidence.mkdir(exist_ok=False)
manifest=json.loads((base/'source_manifest.json').read_text())
for name,sha in manifest.items():
 p=base/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==sha,name
 target=out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
name='sim/oblique_observer_candidate.py';p=out/name
shutil.copy2(root/'.scratch/simulation-reliability/oblique_observer_return_candidate_20261007.py',p)
manifest[name]=hashlib.sha256(p.read_bytes()).hexdigest()
name='sim/navigation_mission.py';p=out/name;s=p.read_text(encoding='utf-8')
needle='    mission_tree.main()';assert s.count(needle)==1
s=s.replace(needle,"    from sim.oblique_observer_candidate import ObliqueObserverReturnBanner\n    mission_tree.FindReturnBanner=ObliqueObserverReturnBanner\n    mission_tree.STATE_NAMES['ObliqueObserverReturnBanner']='RETURN_GATE_SEARCH'\n"+needle)
p.write_bytes(s.encode());manifest[name]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
with zipfile.ZipFile(evidence/'frozen_source.zip','x',zipfile.ZIP_DEFLATED) as z:
 for name in manifest:z.write(out/name,name)
 z.write(out/'source_manifest.json','source_manifest.json')
review=dict(scope='Isolated camera observer handoff on oblique identification plus certified search escapes; object-level navigation only; no production adoption',files=len(manifest),archive_sha256=hashlib.sha256((evidence/'frozen_source.zip').read_bytes()).hexdigest(),accepted_source=False)
(evidence/'provenance.json').write_text(json.dumps(review,indent=2));print(json.dumps(review))
p=root/'.scratch/simulation-reliability/run_certified_search_escape_field_20261007.py';s=p.read_text(encoding='utf-8').replace('certified_search_escape_candidate_20261007','oblique_observer_candidate_20261007').replace('reliability_certified_search_escape_source_20261007','reliability_oblique_observer_source_20261007').replace('reliability_certified_search_escape_field_s','reliability_oblique_observer_field_s')
(root/'.scratch/simulation-reliability/run_oblique_observer_field_20261007.py').write_bytes(s.encode())
