"""Isolate lifetime-peak poisoning; recent observations are not future bounds."""
from pathlib import Path
base=Path(__file__).parent
source=(base/'probe_gust_empirical_profile_reserve_20261007.py').read_text()
# Preserve the original strict-profile guard on the current controller's
# inherited observation map. Its compiled navigation planner has a different
# shortcut implementation, so the old textual guard hook cannot target it.
source=source.replace('planner_method = case.node._planner.plan.__func__',
    'from avoidance.local_planner import LocalPlanner as ClearanceProfilePlanner\nplanner_method = ClearanceProfilePlanner.plan')
source=source.replace('guard = type(base)(clearance=', 'guard = ClearanceProfilePlanner(clearance=')
source=source.replace('forecasts = deque()', 'forecasts = deque()\nerror_history = deque()\nrate_history = deque()')
old='            error_max = max(error_max,float(np.linalg.norm(np.array(self._pos)-predicted)))\n            error_samples += 1'
new='''            error_history.append((stamp,float(np.linalg.norm(np.array(self._pos)-predicted))))
            while error_history and error_history[0][0]<stamp-1.:
                error_history.popleft()
            error_max=max(value for _,value in error_history)
            error_samples=len(error_history)'''
assert source.count(old)==1
source=source.replace(old,new)
old='            rate_max = max(rate_max,float(np.linalg.norm((self._wind_world-previous_wind)/span)))'
new='''            rate_history.append((stamp,float(np.linalg.norm((self._wind_world-previous_wind)/span))))
            while rate_history and rate_history[0][0]<stamp-1.:
                rate_history.popleft()
            rate_max=max(value for _,value in rate_history)'''
assert source.count(old)==1
source=source.replace(old,new)
source=source.replace("diagnostic_policy='empirical forecast-error profile reserve'",
                      "diagnostic_policy='recent empirical forecast reserve; not a future bound',diagnostic_window_s=1.")
exec(compile(source,str(base/'probe_gust_empirical_profile_reserve_20261007.py'),'exec'))
