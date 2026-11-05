"""Close the full offline suite against the exact pre-run code/asset freeze."""
import hashlib,json,re,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from campaign_record import source_manifest
log=root/'logs/reliability_search_braking_campaign_full_offline_20261007.log'
text=log.read_text();assert ' ALL OFFLINE CHECKS PASSED' in text and ' OFFLINE CHECKS FAILED' not in text
match=re.search(r'(\d+) passed, (\d+) skipped in ([\d.]+)s',text);assert match,text[-2000:]
source=root/'logs/reliability_certified_search_escape_source_20261007';provenance=json.loads((source/'provenance.json').read_text());archive=source/'frozen_source.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==provenance['archive_sha256']
with zipfile.ZipFile(archive) as z:
 frozen=json.loads(z.read('source_manifest.json'))
 for name,sha in frozen.items():assert hashlib.sha256(z.read(name)).hexdigest()==sha,name
source_manifest.cache_clear();current=source_manifest(root)
assert current==frozen,'Source changed relative to the pre-run frozen version'
report=dict(scope='Full offline unit/syntax/configuration/frontend suite only; no rendered or coupled gust qualification',all_offline_checks_passed=True,passed=int(match[1]),skipped=int(match[2]),python_tests_elapsed_s=float(match[3]),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),source_archive_sha256=provenance['archive_sha256'],source_files_verified=len(frozen),source_unchanged_since_pre_run_freeze=True,accepted_source=False)
with (root/'logs/reliability_search_braking_campaign_full_offline_closed_review_20261007.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report,indent=2))
