"""Frozen navigation batch with process-local recorder paths and owned cleanup."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import zipfile

root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/combined_observation_motion_candidate_20261007'
qualified=root/'logs/reliability_combined_observation_navigation_source_20261007'
out=root/'logs/reliability_combined_observation_focused_navigation_20261007'
archive_path=qualified/'frozen_source.zip'

if len(sys.argv)>1 and sys.argv[1]=='--worker':
    condition,seed,domain=sys.argv[2:]
    os.chdir(snapshot)
    sys.path[:0]=[str(snapshot),str(snapshot/'sim'),str(snapshot/'scripts')]
    from fly_headless import fly,stop_all
    signal.signal(signal.SIGINT,stop_all);signal.signal(signal.SIGTERM,stop_all)
    name=f'my_world_{condition}_s{seed}'
    assert os.environ['AEROTHON_MOTION_FORECAST_OUT']==str(out/f'{name}_forecasts.json')
    result=fly(snapshot/'sim/worlds/my_world.json',condition,int(seed),out,2.,1200.,int(domain),navigation_only=True)
    (out/f'{name}_worker_result.json').write_text(json.dumps(result,indent=2)+'\n')
    raise SystemExit(0 if result['navigation_pass'] else 1)

review=json.loads((qualified/'candidate_provenance.json').read_text())
assert review['source_archive_verified']
assert '29 passed' in (root/'logs/reliability_combined_observation_checks_owned_20261007/regressions.log').read_text()
assert json.loads((root/'logs/reliability_combined_gate_pause_contract_20261007/report.json').read_text())['passed']
assert hashlib.sha256(archive_path.read_bytes()).hexdigest()==review['source_archive_sha256']
with zipfile.ZipFile(archive_path) as archive:
    frozen=json.loads(archive.read('source_manifest.json'))
    for name,sha in frozen.items():
        assert hashlib.sha256(archive.read(name)).hexdigest()==sha,name
        assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha,name
provenance=json.loads((qualified/'candidate_provenance.json').read_text())
assets=provenance['asset_sha256']
for name,sha in assets.items():
    assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha,name

out.mkdir(exist_ok=False)
(out/'runner_source.py').write_bytes(Path(__file__).read_bytes())
report=dict(scope='Navigation only; no rendered perception or motor-delivery qualification',
    source_archive_sha256=review['source_archive_sha256'],source_files=len(frozen),
    asset_sha256=assets,physical_response_s=.6,physical_command_delay_s=.4,rtf=2.,jobs=2,
    source_unchanged=None,production_adopted=False,started_wall=time.time(),results=[],
    configurations=[dict(condition=c,seed=s,ros_domain=210+i) for i,(c,s) in enumerate(
        [('field',4),('field',5),('calm',5)])])
lock=threading.Lock();stop=threading.Event();workers={}

def save():
    temporary=out/'report.json.writing'
    temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(out/'report.json')

def cleanup(signum,_frame):
    stop.set()
    with lock:
        for process in workers.values():
            if process.poll() is None:os.killpg(process.pid,signal.SIGTERM)
    raise SystemExit(128+signum)

signal.signal(signal.SIGINT,cleanup);signal.signal(signal.SIGTERM,cleanup)
save()

def run(cfg):
    name=f"my_world_{cfg['condition']}_s{cfg['seed']}"
    if stop.is_set():return dict(run=name,executed=False,reason='owned interruption')
    env=dict(os.environ,AEROTHON_MOTION_FORECAST_OUT=str(out/f'{name}_forecasts.json'))
    with (out/f'{name}_worker.log').open('xb') as stream:
        with lock:
            if stop.is_set():return dict(run=name,executed=False,reason='owned interruption')
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker',
                cfg['condition'],str(cfg['seed']),str(cfg['ros_domain'])],cwd=snapshot,env=env,
                stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            workers[name]=process
        code=process.wait()
    with lock:workers.pop(name,None)
    path=out/f'{name}_worker_result.json'
    if not path.exists():return dict(run=name,navigation_pass=False,harness_valid=False,exit_code=code)
    result=json.loads(path.read_text())
    result['source_matches_frozen']=json.loads((out/name/'source_manifest.json').read_text())==frozen
    result['forecast_recording_closed']=(out/f'{name}_forecasts.json').exists()
    result['harness_valid']=result['source_matches_frozen'] and result['forecast_recording_closed']
    result['worker_exit_code']=code
    return result

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    futures=[pool.submit(run,cfg) for cfg in report['configurations']]
    for future in concurrent.futures.as_completed(futures):
        report['results'].append(future.result());save()
        print(json.dumps(report['results'][-1]),flush=True)
report['source_unchanged']=all(hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha
                               for name,sha in {**frozen,**assets}.items())
report.update(finished_wall=time.time(),navigation_passes=sum(
    r.get('navigation_pass',False) and r.get('harness_valid',False) for r in report['results']))
report['all_navigation_pass']=report['source_unchanged'] and all(
    r.get('navigation_pass',False) and r.get('harness_valid',False) for r in report['results'])
save()
raise SystemExit(0 if report['all_navigation_pass'] else 1)
