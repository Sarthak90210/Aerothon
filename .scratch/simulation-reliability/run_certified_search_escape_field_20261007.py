"""One owned field-2 repetition against the frozen integrated normal startup."""
import hashlib,json,os,signal,sys,time,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/certified_search_escape_candidate_20261007'
source=root/'logs/reliability_certified_search_escape_source_20261007'
seed=int(sys.argv[1]) if len(sys.argv)>1 else 2
assert seed in (1,2,3)
out=root/f'logs/reliability_certified_search_escape_field_s{seed}_navigation_20261007'
provenance=json.loads((source/'provenance.json').read_text())
archive=source/'frozen_source.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==provenance['archive_sha256']
with zipfile.ZipFile(archive) as z:
 frozen=json.loads(z.read('source_manifest.json'))
 for name,sha in frozen.items():
  assert hashlib.sha256(z.read(name)).hexdigest()==sha,name
  assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha,name
assets={name:sha for name,sha in frozen.items() if Path(name).suffix in ('.txt','.glb','.png','.jpg')}
assert all(hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha for name,sha in assets.items())
out.mkdir(exist_ok=False);(out/'runner_source.py').write_bytes(Path(__file__).read_bytes())
os.chdir(snapshot);sys.path[:0]=[str(snapshot),str(snapshot/'sim'),str(snapshot/'scripts')]
from fly_headless import fly,stop_all
signal.signal(signal.SIGINT,stop_all);signal.signal(signal.SIGTERM,stop_all)
os.environ.pop('AEROTHON_MOTION_FORECAST_OUT',None)
report=dict(scope=provenance['scope'],archive_sha256=provenance['archive_sha256'],source_files=len(frozen),physical_command_delay_s=.4,physical_response_s=.6,ros_domain=189+seed,conditions='field',seed=seed,rtf=2.,accepted_source=False,asset_sha256=assets,started_wall=time.time())
(out/'report_started.json').write_text(json.dumps(report,indent=2))
result=fly(snapshot/'sim/worlds/my_world.json','field',seed,out,2.,1200.,189+seed,navigation_only=True)
run=out/f'my_world_field_s{seed}'
report.update(result=result,finished_wall=time.time(),source_unchanged=all(hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha for name,sha in frozen.items()),run_manifest_matches_frozen=json.loads((run/'source_manifest.json').read_text())==frozen,asset_unchanged=all(hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha for name,sha in assets.items()),rendered_qualified=False,motor_delivery_qualified=False)
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));raise SystemExit(0 if result['navigation_pass'] and report['source_unchanged'] and report['run_manifest_matches_frozen'] and report['asset_unchanged'] else 1)
