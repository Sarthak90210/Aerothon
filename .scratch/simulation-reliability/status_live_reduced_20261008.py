import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
for seed in (1,2,3):
 prefix=sys.argv[1] if len(sys.argv)>1 else 'reliability_reduced_seed_trials_20261008'
 p=root/f'logs/{prefix}/my_world_field_s{seed}/onboard.jsonl'
 if not p.exists():continue
 with p.open('rb') as f:
  f.seek(max(0,p.stat().st_size-65536));lines=f.read().splitlines()
 for line in reversed(lines):
  try:r=json.loads(line);break
  except (ValueError,UnicodeDecodeError):continue
 else:continue
 print(json.dumps(dict(seed=seed,stamp=r.get('stamp'),mission=r.get('mission'),armed=r.get('flight',{}).get('data',{}).get('armed'),pose=r.get('pose',{}).get('data',{}).get('pose',{}).get('position'),channels=list(r.keys()))))
