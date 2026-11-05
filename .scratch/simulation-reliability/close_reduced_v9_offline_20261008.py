import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from campaign_record import source_manifest
snapshot=root/'.scratch/reduced_scope_v9_candidate_20261008'
manifest=json.loads((snapshot/'source_manifest.json').read_text());source_manifest.cache_clear()
assert manifest==source_manifest(root),'Controlled source set changed during full suite'
assert all(hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
log=root/'logs/reliability_reduced_v9_full_offline_20261008.log'
text=log.read_text();assert 'ALL OFFLINE CHECKS PASSED' in text or 'ALL CHECKS PASSED' in text,text[-800:]
out=root/'logs/reliability_reduced_scope_v9_source_20261008/full_offline_closed_review.json'
review=dict(all_offline_checks_pass=True,source_files=len(manifest),source_unchanged=True,
            log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),accepted_source=False)
with out.open('x') as f:json.dump(review,f,indent=2)
