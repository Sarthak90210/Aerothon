"""Preserve the fourth rejected control experiment and its exact dependencies."""
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'logs/reliability_terminal_replacement_rejection_20261007'
OUT.mkdir(exist_ok=False)
data=(ROOT/'logs/delayed_control_review_terminal_replacement_dirty0_20261007.json').read_bytes()
report=json.loads(data)
summary_path=ROOT/'.scratch/simulation-reliability/delayed_control_review_terminal_replacement_summary_20261007.json'
summary=json.loads(summary_path.read_bytes())
sha=lambda data:hashlib.sha256(data).hexdigest()
assert report['passed'] is False and summary['production_adoption_supported'] is False
assert sha(data)==summary['source_sha256']
sources=dict(report['source_sha256'])
for name,expected in (
    ('.scratch/simulation-reliability/delayed_control_review_smith_probe_20261007.py',report['base_helper_sha256']),
    ('.scratch/simulation-reliability/probe_gust_margin.py',report['probe_template_sha256'])):
    sources[name]=expected
for name in ('.scratch/simulation-reliability/delayed_control_review_analyse_terminal_replacement_20261007.py',
             '.scratch/simulation-reliability/delayed_control_review_run_terminal_replacement_20261007.sh',
             str(Path(__file__).relative_to(ROOT))):
    sources[name]=sha((ROOT/name).read_bytes())
with zipfile.ZipFile(OUT/'source_and_result.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
    for name,expected in sorted(sources.items()):
        content=(ROOT/name).read_bytes()
        assert sha(content)==expected,name
        archive.writestr(name,content)
    archive.writestr('result.json',data)
    archive.writestr('summary.json',summary_path.read_bytes())
    archive.writestr('source_manifest.json',json.dumps(sources,indent=2)+'\n')
with zipfile.ZipFile(OUT/'source_and_result.zip') as archive:
    assert all(sha(archive.read(name))==expected for name,expected in sources.items())
    assert sha(archive.read('result.json'))==summary['source_sha256']
closure=dict(state='CLOSED_REJECTED',archive_verified=True,source_files=len(sources),
    archive_sha256=sha((OUT/'source_and_result.zip').read_bytes()),
    actual_minimum_clearance_m=summary['actual_minimum_clearance_m'],
    first_violation=summary['first_observed_clearance_violation'],
    contact_s=19.05,held_out_trials_run=0,coupled_gust_delay_qualified=False,
    production_adoption_supported=False)
(OUT/'closure.json').write_text(json.dumps(closure,indent=2)+'\n')
print(json.dumps(closure))
