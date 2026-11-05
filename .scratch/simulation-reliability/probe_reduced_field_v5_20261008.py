"""V5 field regressions, two independent domains at a time."""
import hashlib,json,os,signal,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
root=Path(__file__).resolve().parents[2];snapshot=root/'.scratch/reduced_scope_v5_candidate_20261008'
out=root/'logs/reliability_reduced_v5_field_targeted_20261008';out.mkdir(exist_ok=False)
os.chdir(snapshot);sys.path[:0]=[str(snapshot),str(snapshot/'sim'),str(snapshot/'scripts')]
from fly_headless import fly,stop_all
signal.signal(signal.SIGINT,stop_all);signal.signal(signal.SIGTERM,stop_all)
manifest=json.loads((snapshot/'source_manifest.json').read_text());results=[]
def run(seed):return fly(snapshot/'sim/worlds/my_world.json','field',seed,out,4.,1200.,41+seed,navigation_only=True,injected_command_delay_s=0.)
with ThreadPoolExecutor(max_workers=2) as pool:
 for future in as_completed([pool.submit(run,seed) for seed in (1,2,3)]):
  result=future.result();results.append(result);print(json.dumps(result),flush=True)
unchanged=all(hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
report=dict(scope='V5 field regressions; object navigation only',results=results,source_unchanged=unchanged,pass_navigation=unchanged and all(r['navigation_pass'] for r in results))
(out/'report.json').write_text(json.dumps(report,indent=2));raise SystemExit(0 if report['pass_navigation'] else 1)
