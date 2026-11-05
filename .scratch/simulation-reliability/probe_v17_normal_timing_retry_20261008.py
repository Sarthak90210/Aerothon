"""Isolate concurrent-check timing with the same frozen code/configurations."""
import hashlib,json,os,signal,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
root=Path(__file__).resolve().parents[2];snapshot=root/'.scratch/reduced_scope_v17_candidate_20261008'
out=root/'logs/reliability_reduced_v17_normal_timing_retry_20261008';out.mkdir(exist_ok=False)
assert json.loads((root/'logs/reliability_reduced_scope_v17_source_20261008/full_offline_closed_review.json').read_text())['all_offline_checks_pass']
os.chdir(snapshot);sys.path[:0]=[str(snapshot),str(snapshot/'sim'),str(snapshot/'scripts')]
from fly_headless import fly,stop_all
signal.signal(signal.SIGINT,stop_all);signal.signal(signal.SIGTERM,stop_all)
manifest=json.loads((snapshot/'source_manifest.json').read_text());results=[]
cases=[('field',1,41),('field',3,43),('random',3,40)]
with ThreadPoolExecutor(max_workers=2) as pool:
    futures=[pool.submit(fly,snapshot/'sim/worlds/my_world.json',weather,seed,out,2.,1200.,domain,navigation_only=True,injected_command_delay_s=0.) for weather,seed,domain in cases]
    for future in as_completed(futures):
        result=future.result();results.append(result);print(json.dumps(result),flush=True)
unchanged=all(hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
report=dict(scope='Focused normal-timing probe after offline suite; two workers, unchanged source/conditions/ROS domains/actuators/sensor cadence/RTF2/zero added queue',hypotheses=['Concurrent full-suite and five-flight workload perturbs callback timing','Pose/lidar projection error consumes the minimum clearance margin','Wind estimate/response mismatch in return entry','Fresh banner evidence changes recovery duration','Generated world or timing configuration differs'],results=results,source_unchanged=unchanged,pass_navigation=unchanged and all(r['navigation_pass'] for r in results))
(out/'report.json').write_text(json.dumps(report,indent=2));raise SystemExit(0 if report['pass_navigation'] else 1)
