"""Freeze integrated startup, native contact grading and reduced campaign scope."""
import hashlib,json,shutil,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
from campaign_record import source_manifest
out=root/'.scratch/reduced_scope_v6_candidate_20261008';out.mkdir(exist_ok=False)
evidence=root/'logs/reliability_reduced_scope_v6_source_20261008';evidence.mkdir(exist_ok=False)
manifest={name.replace('\\','/'):sha for name,sha in source_manifest(root).items()}
for name,sha in manifest.items():
 p=root/name;target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
 assert hashlib.sha256(p.read_bytes()).hexdigest()==sha,name
 shutil.copy2(p,target)
(out/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
with zipfile.ZipFile(evidence/'frozen_source.zip','x',zipfile.ZIP_DEFLATED) as z:
 for name in manifest:z.write(out/name,name)
 z.write(out/'source_manifest.json','source_manifest.json')
review=dict(scope='Reduced qualification: normal actuator response, no artificial transport queue; strong wind/gust above moderate field envelope excluded',files=len(manifest),archive_sha256=hashlib.sha256((evidence/'frozen_source.zip').read_bytes()).hexdigest(),accepted_source=False,original_200_case_qualified=False)
(evidence/'provenance.json').write_text(json.dumps(review,indent=2));print(json.dumps(review))
