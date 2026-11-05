"""Frozen candidate across five seeds, calm and field; navigation only."""
import concurrent.futures,hashlib,json,os,signal,sys,time,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/braked_navigation_candidate_20261007'
qualified=root/'logs/reliability_live_clock_navigation_candidate_fixed_20261007'
review=json.loads((qualified/'source_archive_review.json').read_text())
assert review['archive_verified'] and review['result']['navigation_pass']
archive_path=qualified/'frozen_source.zip'
assert hashlib.sha256(archive_path.read_bytes()).hexdigest()==review['archive_sha256']
with zipfile.ZipFile(archive_path) as archive:
    frozen=json.loads(archive.read('source_manifest.json'))
    for name,sha in frozen.items():
        assert hashlib.sha256(archive.read(name)).hexdigest()==sha,name
        assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha,name
os.chdir(snapshot)
sys.path.insert(0,str(snapshot));sys.path.insert(0,str(snapshot/'sim'));sys.path.insert(0,str(snapshot/'scripts'))
from fly_headless import fly,stop_all,PKGS
for outer,inner in PKGS:sys.path.insert(0,str(snapshot/'src'/outer/inner))
from mission_bt import mission_tree,mav_commander,leg_router,gate_braking_candidate
from avoidance import velocity_controller
import headless_world,world_spec,sim.navigation_mission as navigation_mission
modules=(mission_tree,mav_commander,leg_router,gate_braking_candidate,velocity_controller,headless_world,world_spec,navigation_mission)
origins={m.__name__:str(Path(m.__file__).resolve()) for m in modules}
assert all(Path(p).is_relative_to(snapshot.resolve()) for p in origins.values())
out=root/'logs/reliability_focused_clock_navigation_domain_retry_20261007';out.mkdir(exist_ok=False)
signal.signal(signal.SIGINT,stop_all);signal.signal(signal.SIGTERM,stop_all)
report=dict(scope='Frozen candidate focused navigation qualification; no rendered or motor evidence',
    source_archive=str(archive_path),source_archive_sha256=review['archive_sha256'],import_origins=origins,
    configurations=[dict(condition=c,seed=s,ros_domain=190+i,rtf=2.) for i,(c,s) in enumerate(
        [('calm',5)]+[('field',s) for s in range(1,6)])],
    physical_response_s=.6,physical_command_delay_s=.4,jobs=2,started_wall=time.time(),results=[],
    production_adopted=False,rendered_qualified=False,motor_delivery_qualified=False)
def save():
    tmp=out/'report.writing';tmp.write_text(json.dumps(report,indent=2)+'\n');tmp.replace(out/'report.json')
assert all(0<=cfg['ros_domain']<=232 for cfg in report['configurations'])
save()
def run(cfg):
    result=fly(snapshot/'sim/worlds/my_world.json',cfg['condition'],cfg['seed'],out,2.,1200.,cfg['ros_domain'],navigation_only=True)
    result['source_matches_frozen']=json.loads((out/result['run']/'source_manifest.json').read_text())==frozen
    assert result['source_matches_frozen']
    return result
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    futures=[pool.submit(run,cfg) for cfg in report['configurations']]
    for future in concurrent.futures.as_completed(futures):
        report['results'].append(future.result());save()
        print(json.dumps(report['results'][-1]),flush=True)
for name,sha in frozen.items():assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha,name
report.update(finished_wall=time.time(),source_unchanged=True,
    navigation_passes=sum(r['navigation_pass'] for r in report['results']),
    all_navigation_pass=all(r['navigation_pass'] for r in report['results']))
save()
raise SystemExit(0 if report['all_navigation_pass'] else 1)
