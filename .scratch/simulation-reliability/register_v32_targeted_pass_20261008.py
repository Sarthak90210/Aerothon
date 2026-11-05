"""Record the targeted gate without accepting rendered or campaign scope."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v32_source_20261008'
review=json.loads((source/'targeted_closed_review.json').read_text())
assert review['pass_navigation'] and review['source_unchanged'] and len(review['results'])==5
lines=['# Current checkpoint: V32 targeted navigation passed; final qualification pending','',
       'All five exact-source targeted cases passed all 13 navigation checks,',
       'with zero contacts/fence breaches and independently recorded connected',
       'actual disarm. Field seeds 1, 2 and 3 and mild random seeds 3 and 4 passed.',
       'Native perception and motor delivery remain unqualified. Random seed 4',
       'retains its DEGRADED visual-landing label; it is not upgraded to PRECISE.','',
       '| Conditions | Seed | Corridor m | Restricted-zone m | Airborne s |',
       '|---|---:|---:|---:|---:|']
for r in review['results']:
    lines.append(f"| {r['weather']} | {r['seed']} | {r['corridor_clearance_m']} | {r['red_clearance_m']} | {r['flight_time_s']} |")
lines+=['','The one final offline suite is next, followed by five exact-source native',
        '22/22 acceptances and 96 eligible campaign flights. Strong gusts and',
        'artificially delayed control remain unresolved and excluded; original',
        'failures remain unchanged. No reduced qualification completion or',
        'original 200-case qualification is claimed.','','']
head='\n'.join(lines)
for name in ('status.md','evidence_report_20261007.md'):
    f=base/name;s=f.read_text(encoding='utf-8')
    if '# Current checkpoint: V32 targeted navigation passed' not in s:
        f.write_text(head+s,encoding='utf-8')
f=base/'evidence_index_20261007.json';index=json.loads(f.read_text())
index['current_continuation'].update(source='V32 provisional; targeted navigation passed',remaining='Final offline suite, five rendered acceptances, 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v32_full_offline_20261008.log']
index['active_trial']=None
index['verification']['v32_targeted_closed_review']='logs/reliability_reduced_scope_v32_source_20261008/targeted_closed_review.json'
index['accepted_source']=None;index['qualification_complete']=False
f.write_text(json.dumps(index,indent=2),encoding='utf-8')
print('All five targeted navigation passes registered; acceptance remains pending')
