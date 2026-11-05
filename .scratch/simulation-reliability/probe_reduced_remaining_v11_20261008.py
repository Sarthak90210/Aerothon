"""Requested fields and retained mild weather on one source and normal timing."""
import hashlib,json,os,signal,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
root=Path(__file__).resolve().parents[2];snapshot=root/'.scratch/reduced_scope_v11_candidate_20261008'
assert json.loads((root/'logs/reliability_reduced_v11_targeted_20261008/report.json').read_text())['pass_navigation'], 'Primary mild-weather regression has not passed'
out=root/'logs/reliability_reduced_v11_remaining_targeted_20261008';out.mkdir(exist_ok=False)
os.chdir(snapshot);sys.path[:0]=[str(snapshot),str(snapshot/'sim'),str(snapshot/'scripts')]
from fly_headless import fly,stop_all
signal.signal(signal.SIGINT,stop_all);signal.signal(signal.SIGTERM,stop_all)
manifest=json.loads((snapshot/'source_manifest.json').read_text());results=[]
cases=[('field',1),('field',2),('field',3),('random',4)]
# Each worker keeps its own low ROS domain as cases are queued sequentially.
def worker(domain,work):
 result=[]
 for weather,seed in work:
  r=fly(snapshot/'sim/worlds/my_world.json',weather,seed,out,2.,1200.,domain,navigation_only=True,injected_command_delay_s=0.)
  result.append(r);print(json.dumps(r),flush=True)
 return result
with ThreadPoolExecutor(max_workers=2) as pool:
 for future in as_completed([pool.submit(worker,40+i,cases[i::2]) for i in (0,1)]):results.extend(future.result())
unchanged=all(hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
report=dict(scope='Five targeted object-navigation regressions; normal actuator response .6s, budget .20s, extra queue zero, RTF2',results=results,source_unchanged=unchanged,pass_navigation=unchanged and all(r['navigation_pass'] for r in results))
(out/'report.json').write_text(json.dumps(report,indent=2));raise SystemExit(0 if report['pass_navigation'] else 1)
