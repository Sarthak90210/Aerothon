"""Compare actual original and instrumented emissions under identical inputs."""
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];snapshot=root/'.scratch/motion_forecast_candidate_20261007'
sys.path.insert(0,str(snapshot/'src/aerothon_avoidance/avoidance'))
from avoidance import velocity_controller
from avoidance.motion_forecast_trace import MotionForecastTrace
sys.path.insert(0,str(snapshot/'sim'))
from test_corridor_clearance_contract import controller
from test_velocity_command_delay import (test_pending_command_is_included_in_stop_clearance,
    test_unknown_prior_target_cannot_shorten_handover_stopping_distance)
from rosidl_runtime_py.convert import message_to_ordereddict
from rclpy.time import Time
from types import SimpleNamespace
out=root/'logs/reliability_motion_forecast_trace_checks_fixed_20261007';out.mkdir(exist_ok=False)
cases=[]
for test in (test_pending_command_is_included_in_stop_clearance,test_unknown_prior_target_cannot_shorten_handover_stopping_distance):
    emissions=[]
    for instrumented in (False,True):
        fixture=controller.__wrapped__();c,sent=next(fixture)
        # _now was already fixed by the fixture; freeze the outgoing ROS
        # header clock as well so both emissions have identical time inputs.
        c.get_clock=lambda:SimpleNamespace(now=lambda:Time(seconds=1.0))
        try:
            if instrumented:trace=MotionForecastTrace(c,out/(test.__name__+'.json'))
            test((c,sent));emissions.append([message_to_ordereddict(m) for m in sent])
            if instrumented:
                assert trace.records and trace.records[-1]['predictions']
                trace.close()
        finally:
            try:next(fixture)
            except StopIteration:pass
    assert emissions[0]==emissions[1],test.__name__
    cases.append(dict(test=test.__name__,identical_emissions=True,original_regression_pass=True))
report=dict(scope='Instrumentation equivalence only, no flight qualification',cases=cases,passed=True)
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
