import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path[:0]=[str(root/'sim'),str(root/'scripts')]
from run_navigation_campaign import reduced_weather_exclusion
worlds=sorted((root/'sim/worlds').glob('*.json'));included=[];excluded=[]
for world in worlds:
 for preset in ('calm','field','worst','random'):
  for seed in range(1,6):
   item=dict(world=world.name,preset=preset,seed=seed)
   reason=reduced_weather_exclusion(preset,seed)
   if reason:excluded.append(dict(item,**reason))
   else:included.append(item)
result=dict(original_matrix=len(worlds)*20,selected_cases=len(included),excluded_weather_cases=len(excluded),
    world_count=len(worlds),included=included,excluded=excluded,
    scope='Wind mean <=4 m/s and gust <=2 m/s, the existing moderate field preset; no injected command delay, normal .6 s physical actuator response',
    geometry_classification_pending=True,executed_cases=0,qualified=False,original_200_case_qualified=False)
path=root/'logs/reliability_reduced_scope_source_20261008/planned_campaign_scope.json'
with path.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ('included','excluded')},indent=2))
