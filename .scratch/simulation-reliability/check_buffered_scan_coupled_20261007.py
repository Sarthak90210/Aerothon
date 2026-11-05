"""Preserved gust/delay cases against buffered observations with stamped fixtures."""
import hashlib,json,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/buffered_scan_motion_candidate_20261007'
fixtures=root/'.scratch/buffered_stamped_regression_fixtures_20261007'
archive=root/'logs/reliability_buffered_stamped_fixture_preparation_20261007/rejected_regression_source.zip'
with zipfile.ZipFile(archive) as source:
    frozen=json.loads(source.read('source_manifest.json'))
    for name,sha in frozen.items():assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha,name
sys.path[:0]=[str(snapshot/'src/aerothon_avoidance/avoidance'),str(snapshot/'src/aerothon_sim/sim_gazebo'),str(fixtures)]
import test_slalom_traverse as slalom
assert Path(slalom.__file__).resolve().is_relative_to(fixtures.resolve())
from avoidance import velocity_controller,buffered_scan_pose
initialize=velocity_controller.VelocityController.__init__
def initialized(node,*a,**kw):initialize(node,*a,**kw);buffered_scan_pose.install(node)
velocity_controller.VelocityController.__init__=initialized
sys.path.insert(0,str(snapshot/'sim'))
import test_corridor_stress as stress
assert stress.slalom is slalom
out=root/'logs/reliability_buffered_scan_coupled_20261007';out.mkdir(exist_ok=False)
(out/'runner_source.py').write_bytes(Path(__file__).read_bytes())
(out/'stamped_slalom_fixture.py').write_bytes((fixtures/'test_slalom_traverse.py').read_bytes())
summary=[]
for kind,seed in [('dirty',0),('late',1)]:
    case=stress.SplitLaneStressTests('test_gusty_crosswind');case.setUpClass();case.setUp()
    rows=[];publish=case.node._publish
    def capture(*a,**kw):
        publish(*a,**kw);x,y=case.node._pos
        rows.append(dict(stamp=case.node._now(),pose=[x,y],
            independent_preintegration_clearance_m=min(slalom.gap_to(x,y,r) for r in slalom.WALLS+slalom.BLOCKS),
            detail=case.node.last_detail,scan_pairing_reason=case.node._scan_pairing_reason))
    case.node._publish=capture
    passed=False;failure=None
    try:
        options=dict(corrupt=stress.dirty_lidar(seed)) if kind=='dirty' else dict(scan_delay_s=.15)
        case._through(drift=stress.WindDrift(seed=seed),command_delay_s=.4,**options);passed=True
    except AssertionError as error:failure=str(error)
    finally:
        result=dict(kind=kind,seed=seed,passed=passed,failure=failure,rows=rows,
            physical_command_delay_s=.4,physical_response_s=.6,physical_fixture_changed=False,
            capture_timestamps_added=True,source_archive=str(archive),
            source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
            scope='Offline coupled physical fixture; truth used only for evaluation')
        (out/f'{kind}_s{seed}.json').write_text(json.dumps(result)+'\n')
        summary.append(dict(kind=kind,seed=seed,passed=passed,records=len(rows),
            minimum_logged_preintegration_clearance_m=min(r['independent_preintegration_clearance_m'] for r in rows),failure=failure))
        case.tearDown();case.tearDownClass()
    print(json.dumps(summary[-1]),flush=True)
(out/'summary.json').write_text(json.dumps(dict(cases=summary,all_pass=all(r['passed'] for r in summary),production_adopted=False),indent=2)+'\n')
raise SystemExit(0 if all(r['passed'] for r in summary) else 1)
