"""One owned, frozen navigation trial; unique recorder and unchanged physical model."""
import hashlib,json,os,signal,sys,time,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/buffered_scan_motion_candidate_20261007'
archive_path=root/'logs/reliability_buffered_stamped_fixture_preparation_20261007/rejected_regression_source.zip'
review=json.loads((archive_path.parent/'report.json').read_text())
assert review['rejected_source_archive_verified']
assert hashlib.sha256(archive_path.read_bytes()).hexdigest()==review['rejected_archive_sha256']
with zipfile.ZipFile(archive_path) as archive:
    frozen=json.loads(archive.read('source_manifest.json'))
    for name,sha in frozen.items():
        assert hashlib.sha256(archive.read(name)).hexdigest()==sha,name
        assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha,name
provenance=json.loads((snapshot/'candidate_provenance.json').read_text())
assets=provenance['asset_sha256']
for name,sha in assets.items():assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha,name
check=root/'logs/reliability_buffered_scan_stamped_regressions_owned_20261007'
assert json.loads((check/'status.json').read_text())['state']=='COMPLETED'
assert '29 passed' in (check/'output.log').read_text()
os.chdir(snapshot);sys.path[:0]=[str(snapshot),str(snapshot/'sim'),str(snapshot/'scripts')]
from fly_headless import fly,stop_all,PKGS
for outer,inner in PKGS:sys.path.insert(0,str(snapshot/'src'/outer/inner))
from avoidance import velocity_controller,buffered_scan_pose
assert all(Path(module.__file__).resolve().is_relative_to(snapshot.resolve())
           for module in (velocity_controller,buffered_scan_pose))
out=root/'logs/reliability_buffered_scan_navigation_seed3_20261007';out.mkdir(exist_ok=False)
(out/'runner_source.py').write_bytes(Path(__file__).read_bytes())
(out/'candidate_provenance.json').write_bytes((snapshot/'candidate_provenance.json').read_bytes())
os.environ['AEROTHON_MOTION_FORECAST_OUT']=str(out/'motion_forecasts.json')
report=dict(state='RUNNING',source_archive=str(archive_path),source_archive_sha256=review['rejected_archive_sha256'],
    source_files=len(frozen),asset_sha256=assets,started_wall=time.time(),
    physical_response_s=.6,physical_command_delay_s=.4,seed=3,condition='calm',
    scope='Navigation only; no rendered perception or motor-delivery qualification',production_adopted=False)
def save():
    temporary=out/'report.json.writing';temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(out/'report.json')
save();signal.signal(signal.SIGINT,stop_all);signal.signal(signal.SIGTERM,stop_all)
result=fly(snapshot/'sim/worlds/my_world.json','calm',3,out,2.,1200.,226,navigation_only=True)
recorded=json.loads((out/'my_world_calm_s3/source_manifest.json').read_text())
assert recorded==frozen
unchanged=all(hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha for name,sha in {**frozen,**assets}.items())
report.update(state='COMPLETED',result=result,source_unchanged=unchanged,
    forecast_recording_closed=(out/'motion_forecasts.json').exists(),finished_wall=time.time())
save();print(json.dumps(report),flush=True)
raise SystemExit(0 if unchanged and result['navigation_pass'] and report['forecast_recording_closed'] else 1)
