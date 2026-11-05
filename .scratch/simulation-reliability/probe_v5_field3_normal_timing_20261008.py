"""Retry isolated DDS startup failure on a low, non-ephemeral ROS domain."""
import hashlib,json,os,signal,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];snapshot=root/'.scratch/reduced_scope_v5_candidate_20261008'
out=root/'logs/reliability_reduced_v5_seed3_normal_timing_retry_20261008';out.mkdir(exist_ok=False)
os.chdir(snapshot);sys.path[:0]=[str(snapshot),str(snapshot/'sim'),str(snapshot/'scripts')]
from fly_headless import fly,stop_all
signal.signal(signal.SIGINT,stop_all);signal.signal(signal.SIGTERM,stop_all)
manifest=json.loads((snapshot/'source_manifest.json').read_text())
result=fly(snapshot/'sim/worlds/my_world.json','field',3,out,2.,1200.,42,navigation_only=True,injected_command_delay_s=0.)
unchanged=all(hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
report=dict(scope='Same frozen V5 and normal actuator/timing budget; reduce simulation real-time factor from 4 to 2 after observed computation deadline overrun',result=result,source_unchanged=unchanged,pass_navigation=unchanged and result['navigation_pass'],rendered_qualified=False)
(out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));raise SystemExit(0 if report['pass_navigation'] else 1)
