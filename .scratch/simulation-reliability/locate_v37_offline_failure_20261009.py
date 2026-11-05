import json,re
from pathlib import Path
root=Path(__file__).resolve().parents[2]
ledger=json.loads((root/'logs/reliability_reduced_scope_v37_source_20261008/offline_scope_exclusions.json').read_text())
progress=[]
for line in (root/'logs/reliability_reduced_v37_full_offline_20261008.log').read_text().splitlines():
 m=re.fullmatch(r'([.FsSEx]+)(?:\s+\[\s*\d+%\])?\s*',line)
 if m:progress.extend(m.group(1))
for i,c in enumerate(progress):
 if c=='F':
  print('Failed ordinal',i+1,'provisional included node',ledger['included_nodes'][i])
  print('Nearby nodes',json.dumps(ledger['included_nodes'][max(0,i-2):i+3]))
print('Observed progress items',len(progress),'of',ledger['collected_tests'])
