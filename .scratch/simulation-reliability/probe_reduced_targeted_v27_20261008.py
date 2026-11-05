"""Requested fields and retained mild weather on one source and normal timing."""
import hashlib,json,os,signal,sys,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from threading import Event
root=Path(__file__).resolve().parents[2];snapshot=root/'.scratch/reduced_scope_v27_candidate_20261008'
out=root/'logs/reliability_reduced_v27_targeted_20261008';out.mkdir(exist_ok=False)
os.chdir(snapshot);sys.path[:0]=[str(snapshot),str(snapshot/'sim'),str(snapshot/'scripts')]
from fly_headless import fly,stop_all
signal.signal(signal.SIGINT,stop_all);signal.signal(signal.SIGTERM,stop_all)
manifest=json.loads((snapshot/'source_manifest.json').read_text());results=[]
stop_queue=Event()
cases=[('random',3),('field',2),('field',1),('field',3),('random',4)]
# Each worker keeps its own low ROS domain as cases are queued sequentially.
def worker(domain,work):
 result=[]
 if domain==40:
  previous=root/'logs/reliability_reduced_v26_targeted_20261008/report.json'
  while not previous.exists():
   if stop_queue.is_set():return result
   time.sleep(2)
 for weather,seed in work:
  if stop_queue.is_set():break
  r=fly(snapshot/'sim/worlds/my_world.json',weather,seed,out,2.,1200.,domain,navigation_only=True,injected_command_delay_s=0.)
  result.append(r);print(json.dumps(r),flush=True)
  if not r['navigation_pass']:stop_queue.set()
 return result
with ThreadPoolExecutor(max_workers=2) as pool:
 for future in as_completed([pool.submit(worker,41-i,cases[i::2]) for i in range(2)]):results.extend(future.result())
unchanged=all(hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
report=dict(scope='Five normal-timing targeted navigation regressions; native-matching camera 20 Hz and lidar 10 Hz, normal actuator response .6s, budget .20s, extra queue zero, RTF2',results=results,source_unchanged=unchanged,pass_navigation=unchanged and len(results)==len(cases) and all(r['navigation_pass'] for r in results),planned_cases=len(cases),executed_cases=len(results),cancelled_unflown_cases=len(cases)-len(results))
(out/'report.json').write_text(json.dumps(report,indent=2));raise SystemExit(0 if report['pass_navigation'] else 1)
