"""Diagnostic fixture timing probes; original six-replan/coverage assertions stay."""
import inspect,sys,textwrap
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
import test_fail_closed_stages as tests
original=textwrap.dedent(inspect.getsource(tests.FrontierSearchTests._clip_not_drop))
for period in (1,2,3,5,10,20):
    source=original.replace('min(tick + 1, 40)',f'min(tick // {period} + 1, 40)')
    namespace=dict(vars(tests));exec(compile(source,'<diagnostic-fixture-schedule>','exec'),namespace)
    case=tests.FrontierSearchTests('test_red_lane_end_clips_the_lane_instead_of_dropping_it')
    case.setUp()
    try:
        namespace['_clip_not_drop'](case,replan_min_ticks=0)
        result='PASS: original six-replan, zero-skip and lane-coverage assertions'
    except AssertionError as error:result=str(error)
    finally:case.tearDown()
    print(period,result,flush=True)
