import json,re,sys
from pathlib import Path
root=Path.cwd()
for version in ('v7','v13'):
 parent=root/'logs'/f'reliability_reduced_{version}_'+Path('x') if False else root/'logs'/('reliability_reduced_v7_random_targeted_20261008' if version=='v7' else 'reliability_reduced_v13_targeted_20261008')
 for run in parent.glob('my_world_*'):
  lines=(run/'onboard.jsonl').read_text(encoding='utf-8').splitlines();rows=[]
  for s in lines:
   try:rows.append(json.loads(s))
   except ValueError:pass
  if not rows:continue
  row=rows[-1];log=(run/'stack.log').read_text(encoding='utf-8')
  xyz=row.get('pose',{}).get('data',{}).get('pose',{}).get('position',{})
  changes=[];prev=None
  for r in rows:
   phase=r.get('mission')
   if phase!=prev:changes.append((round(r['stamp'],1),phase));prev=phase
  print(version,run.name,json.dumps(dict(stamp=round(row['stamp'],1),pose=xyz,phase=changes,brakes=log.count('search segment invalidated'),replans=log.count('re-planned'),skipped=log.count('skipping waypoint'))))
