"""Freeze all code and shipped assets through the shared source recorder."""
import hashlib,json,shutil,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
from campaign_record import source_manifest
out=root/'.scratch/scoped_escape_root_candidate_20261007';out.mkdir(exist_ok=False)
evidence=root/'logs/reliability_scoped_escape_root_source_20261007';evidence.mkdir(exist_ok=False)
manifest=source_manifest(root)
for name,sha in manifest.items():
 path=root/name;target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
 assert hashlib.sha256(path.read_bytes()).hexdigest()==sha,name
 shutil.copy2(path,target)
normalized={name.replace('\\','/'):sha for name,sha in manifest.items()}
(out/'source_manifest.json').write_text(json.dumps(normalized,indent=2))
with zipfile.ZipFile(evidence/'frozen_source.zip','x',zipfile.ZIP_DEFLATED) as z:
 for name in normalized:z.write(out/name,name)
 z.write(out/'source_manifest.json','source_manifest.json')
review=dict(scope='Outward nearest-edge escape continuation requires nondecreasing distance to each containing observed paint margin; other margins retain full segment checks; current normal startup; object-level navigation only',files=len(normalized),archive_sha256=hashlib.sha256((evidence/'frozen_source.zip').read_bytes()).hexdigest(),accepted_source=False)
(evidence/'provenance.json').write_text(json.dumps(review,indent=2));print(json.dumps(review))
