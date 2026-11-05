import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path[:0]=[str(root/'scripts'),str(root/'sim')]
import world_spec as W
from check_corridor_clearance import audit
from run_navigation_campaign import reduced_weather_exclusion
classified=[];selected=excluded=executed_plan=0
for path in sorted((root/'sim/worlds').glob('*.json')):
 errors,warnings=W.validate(W.load(path));geometry=[] if errors else [audit(path,lane_key=lane) for lane in ('corridor','return_corridor')]
 blocked=any(g['classification']=='geometrically blocked' for g in geometry)
 status='invalid fixture' if errors else 'infeasible at 0.70 m' if blocked else 'navigation trial required'
 chosen=sum(reduced_weather_exclusion(preset,seed) is None for preset in ('calm','field','worst','random') for seed in range(1,6))
 selected+=chosen;excluded+=20-chosen;executed_plan+=chosen if not errors and not blocked else 0
 classified.append(dict(world=path.name,classification=status,geometry=geometry,errors=errors,selected=chosen))
report=dict(original_matrix=200,selected=selected,excluded_weather=excluded,planned_flights=executed_plan,classified_without_flight=selected-executed_plan,classified=classified,executed=0,qualified=False)
p=root/'logs/reliability_reduced_scope_v32_source_20261008/planned_geometry_scope.json';p.write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='classified'}));print(json.dumps([(x['world'],x['classification']) for x in classified]))
