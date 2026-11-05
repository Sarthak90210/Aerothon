"""Record unchanged certificate predictions for two preserved physical failures."""
from pathlib import Path
path=Path(__file__).with_name('check_clock_candidate_coupled_20261007.py')
source=path.read_text()
source=source.replace("out=root/'logs/reliability_clock_candidate_coupled_20261007'",
    "out=root/'logs/reliability_coupled_motion_forecasts_20261007'")
needle='    rows=[];original=case.node._publish'
assert source.count(needle)==1
source=source.replace(needle,"""    import importlib.util
    spec=importlib.util.spec_from_file_location('forecast_trace',Path(__file__).with_name('motion_forecast_trace_candidate_20261007.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    trace=module.MotionForecastTrace(case.node,out/f'{kind}_s{seed}_forecasts.json')
    rows=[];original=case.node._publish""")
source=source.replace('        case.tearDown();case.tearDownClass()',
    '        trace.close();case.tearDown();case.tearDownClass()')
exec(compile(source,str(path),'exec'),dict(__file__=str(path),__name__='__main__'))
