"""Full navigation candidate; all failures retain their independent grade."""
import hashlib,json,os,signal,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.chdir(root)
sys.path.insert(0,str(root))
sys.path.insert(0,str(root/'sim'))
sys.path.insert(0,str(root/'scripts'))
from fly_headless import fly,stop_all,PKGS
for outer,inner in PKGS:
    sys.path.insert(0,str(root/'src'/outer/inner))
from mission_bt import mission_tree,mav_commander,leg_router,gate_braking_candidate
from avoidance import velocity_controller
import headless_world,world_spec
import sim.navigation_mission as navigation_mission
modules=(mission_tree,mav_commander,leg_router,gate_braking_candidate,velocity_controller,headless_world,world_spec,navigation_mission)
origins={module.__name__:str(Path(module.__file__).resolve()) for module in modules}
assert all(Path(path).is_relative_to(root.resolve()) for path in origins.values()),origins
workspace=root.parents[1]
out=workspace/'logs/reliability_live_clock_navigation_candidate_fixed_20261007'
out.mkdir(exist_ok=False)
(out/'import_origins.json').write_text(json.dumps(origins,indent=2)+'\n')
(out/'candidate_provenance.json').write_bytes((root/'candidate_provenance.json').read_bytes())
signal.signal(signal.SIGINT,stop_all);signal.signal(signal.SIGTERM,stop_all)
result=fly(root/'sim/worlds/my_world.json','calm',1,out,4.,1200.,228,navigation_only=True)
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
recorded=json.loads((out/'my_world_calm_s1/source_manifest.json').read_text())
with zipfile.ZipFile(out/'frozen_source.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
    for name,sha in sorted(recorded.items()):
        data=(root/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==sha,name
        archive.writestr(name,data)
    archive.writestr('source_manifest.json',json.dumps(recorded,indent=2)+'\n')
with zipfile.ZipFile(out/'frozen_source.zip') as archive:
    assert all(hashlib.sha256(archive.read(name)).hexdigest()==sha for name,sha in recorded.items())
(out/'source_archive_review.json').write_text(json.dumps(dict(
    source_files=len(recorded),archive_verified=True,
    archive_sha256=hashlib.sha256((out/'frozen_source.zip').read_bytes()).hexdigest(),
    result=result,rendered_perception_qualified=False,motor_delivery_qualified=False),indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['navigation_pass'] else 1)
