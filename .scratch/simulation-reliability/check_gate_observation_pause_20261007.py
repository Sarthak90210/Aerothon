"""Verify no gate movement or handover while paused; qualify recovery separately."""
import hashlib,json,runpy,sys
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'src/aerothon_mission/mission_bt'),str(Path(__file__).parent)]
out=root/'logs/reliability_gate_observation_pause_contract_20261007';out.mkdir(exist_ok=False)
sys.argv=[sys.argv[0],'--out',str(out/'original_gate_contract.json')]
baseline=runpy.run_path(str(Path(__file__).with_name('check_gate_braking_faults_20261007.py')))
from gate_observation_pause_candidate_20261007 import ObservationPausedGateAdvance
from gate_advance_braking_candidate_20261007 import RUNNING,FAILURE,SUCCESS
GateAdvance=baseline['GateAdvance'];Mav=baseline['Mav']
checks=[]
def actor():
    mav=Mav();leaf=ObservationPausedGateAdvance(mav,gate_speed_mps=.5)
    leaf.initialise();leaf._target=(16.,-15.);leaf._flight_alt=2.
    routes=[];leaf.router=NS(fly=lambda *args:routes.append(args))
    return mav,leaf,routes
mav,leaf,routes=actor()
with patch.object(GateAdvance,'update',return_value=RUNNING) as crossing:
    assert leaf.update()==RUNNING
    before=crossing.call_count
    mav.t=2.;mav.xyz=(16.,-15.,2.);mav.observe();mav._scan.header.stamp.sec=1
    assert leaf.update()==RUNNING and crossing.call_count==before and not routes
    assert mav.commands[-1]==mav.xyz and not mav.abort_reason
    mav.t=2.2;mav.observe();assert leaf.update()==RUNNING
    assert crossing.call_count==before+1 and leaf._observation_wait_started is None
checks.append('transient stale scan holds latest measured pose and resumes only with fresh captures')
mav,leaf,routes=actor()
with patch.object(GateAdvance,'update',return_value=RUNNING) as crossing:
    assert leaf.update()==RUNNING
    mav.t=2.;mav.xyz=(999.,999.,2.)
    assert leaf.update()==RUNNING and mav.commands[-1]==(20.,-16.,2.)
    before=crossing.call_count
    mav.t=3.01;assert leaf.update()==FAILURE and crossing.call_count==before
    assert 'bounded gate hold' in mav.abort_reason
checks.append('sustained observation loss fails within the bounded pause and never uses stale pose')
mav,leaf,routes=actor()
with patch.object(GateAdvance,'update',return_value=SUCCESS):
    assert leaf.update()==RUNNING and leaf._settle_count==1
    mav.t=1.4;assert leaf.update()==RUNNING and leaf._settle_count==0
    for t in (1.5,1.7,1.9):
        mav.t=t;mav.observe();result=leaf.update()
    assert result==SUCCESS and mav.speed_requests==[.5,5.]
checks.append('observation gap resets dwell and requires three new velocity captures before handover')
mav,leaf,routes=actor();mav.response='rejected'
with patch.object(GateAdvance,'update',return_value=SUCCESS) as crossing:
    assert leaf.update()==FAILURE;crossing.assert_not_called()
checks.append('service rejection remains immediate failure')
mav,leaf,routes=actor();mav.t=61.01;mav.observe()
assert leaf.update()==FAILURE
checks.append('overall gate timeout is preserved')
module=Path(__file__).with_name('gate_observation_pause_candidate_20261007.py')
(out/module.name).write_bytes(module.read_bytes())
report=dict(passed=True,checks=checks,original_contract_checks=len(baseline['results']),
    source_sha256=hashlib.sha256(module.read_bytes()).hexdigest(),production_adopted=False,
    scope='Gate callback and stop-anchor contract; no physical or full-flight qualification')
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(passed=True,checks=len(checks),original_checks=len(baseline['results']))))
