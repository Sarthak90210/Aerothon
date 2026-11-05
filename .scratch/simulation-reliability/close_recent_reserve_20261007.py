"""Close the rejected recent-reserve diagnostic, preserving all three failures."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];out=root/'logs/reliability_recent_reserve_coupled_retry_20261007'
results={}
for name in ('dirty_gust','late_gust','dirty_calm'):
 r=json.loads((out/f'{name}.json').read_text())
 assert not r['passed']
 for path,sha in r['source_sha256'].items():assert hashlib.sha256((root/path).read_bytes()).hexdigest()==sha,path
 results[name]={k:r[k] for k in ('passed','minimum_actual_clearance_m','command_delay_s','kind','seed','diagnostic_wind_profile')}
 results[name]['failure']=r['failure'].split('; detail ')[0]
for original,copy in [('probe_gust_recent_reserve_20261007.py','runner_source.py'),('probe_gust_empirical_profile_reserve_20261007.py','baseline_policy_source.py'),('probe_gust_margin.py','physical_probe_source.py')]:
 assert (root/'.scratch/simulation-reliability'/original).read_bytes()==(out/copy).read_bytes()
review=dict(scope='Rejected empirical-window diagnostic; offline physical fixture, not native qualification',production_installed=False,source_unchanged=True,physical_delay_s=.4,physical_response_s=.6,required_clearance_m=.70,results=results,files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()})
with (out/'closed_review_20261007.json').open('x') as f:json.dump(review,f,indent=2)
print(json.dumps(results,indent=2))
