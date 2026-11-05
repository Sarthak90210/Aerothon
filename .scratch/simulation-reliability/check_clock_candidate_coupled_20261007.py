"""Replay two preserved coupled failures against frozen candidate bytes."""
import hashlib,json,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/braked_navigation_candidate_20261007'
archive=root/'logs/reliability_live_clock_navigation_candidate_fixed_20261007/frozen_source.zip'
with zipfile.ZipFile(archive) as z:
    frozen=json.loads(z.read('source_manifest.json'))
    for name,sha in frozen.items():assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha,name
sys.path.insert(0,str(snapshot/'src/aerothon_avoidance/avoidance'))
from avoidance import velocity_controller
assert Path(velocity_controller.__file__).resolve().is_relative_to(snapshot.resolve())
sys.path.insert(0,str(snapshot/'sim'))
import test_corridor_stress as stress
import test_slalom_traverse as slalom
assert Path(slalom.__file__).resolve().is_relative_to(snapshot.resolve())
out=root/'logs/reliability_clock_candidate_coupled_20261007';out.mkdir(exist_ok=False)
summary=[]
for kind,seed in [('dirty',0),('late',1)]:
    case=stress.SplitLaneStressTests('test_gusty_crosswind');case.setUpClass();case.setUp()
    rows=[];original=case.node._publish
    def capture(*a,**kw):
        original(*a,**kw)
        x,y=case.node._pos
        rows.append(dict(stamp=case.node._now(),pose=[x,y],
            independent_preintegration_clearance_m=min(slalom.gap_to(x,y,r) for r in slalom.WALLS+slalom.BLOCKS),
            detail=case.node.last_detail))
    case.node._publish=capture
    options=dict(corrupt=stress.dirty_lidar(seed)) if kind=='dirty' else dict(scan_delay_s=.15)
    passed=False;failure=None
    try:
        case._through(drift=stress.WindDrift(seed=seed),command_delay_s=.4,**options)
        passed=True
    except AssertionError as error:failure=str(error)
    finally:
        result=dict(kind=kind,seed=seed,passed=passed,failure=failure,rows=rows,
            physical_command_delay_s=.4,physical_response_s=.6,physical_fixture_changed=False,
            source_archive=str(archive),source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
            scope='Offline coupled-condition fixture; simulator clearance used only for independent evaluation')
        (out/f'{kind}_s{seed}.json').write_text(json.dumps(result)+'\n')
        summary.append(dict(kind=kind,seed=seed,passed=passed,
            minimum_logged_preintegration_clearance_m=min(r['independent_preintegration_clearance_m'] for r in rows),
            records=len(rows),failure=failure))
        case.tearDown();case.tearDownClass()
    print(json.dumps(summary[-1]),flush=True)
(out/'summary.json').write_text(json.dumps(dict(cases=summary,
    all_pass=all(r['passed'] for r in summary),production_adopted=False),indent=2)+'\n')
raise SystemExit(0 if all(r['passed'] for r in summary) else 1)
