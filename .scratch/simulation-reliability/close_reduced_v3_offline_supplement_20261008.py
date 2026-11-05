"""Close unchanged-source full offline checks plus environment-only frontend retry."""
import hashlib,json,re,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from campaign_record import source_manifest
manifest=json.loads((root/'.scratch/reduced_scope_v3_candidate_20261008/source_manifest.json').read_text())
source_manifest.cache_clear();assert manifest==source_manifest(root)
main=root/'logs/reliability_reduced_v3_full_offline_20261008.log';text=main.read_text()
assert '1477 passed, 3 skipped' in text
for section in ('Python unit tests','Python syntax (all mission/perception/GCS/sim sources)','Shell syntax','XML / YAML well-formedness'):
 part=text.split('=== '+section+' ===',1)[1].split('=== ',1)[0]
 assert '-> ok' in part,section
frontend=root/'logs/reliability_reduced_v3_frontend_retry_20261008.log'
assert frontend.read_text().rstrip().endswith('FRONTEND_BUILD_PASS')
review=dict(all_offline_checks_pass=True,python_tests_passed=1477,python_tests_skipped=3,
 source_files=len(manifest),source_unchanged=True,original_environment_failure_preserved=True,
 environment_failure='WSL login did not expose installed Node; original full-suite frontend step could not execute',
 frontend_runtime='/home/sarthak/.nvm/versions/node/v24.18.0/bin/node',
 files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (main,frontend)},accepted_source=False)
with (root/'logs/reliability_reduced_scope_v3_source_20261008/full_offline_closed_review.json').open('x') as f:json.dump(review,f,indent=2)
print(json.dumps(review,indent=2))
