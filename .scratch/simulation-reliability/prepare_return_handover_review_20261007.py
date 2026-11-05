"""Adapt the closed-flight diagnostic to its measured return transition."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
run=root/'logs/reliability_braked_navigation_candidate_restore_config_20261007/my_world_calm_s1'
rows=[json.loads(line) for line in (run/'onboard.jsonl').read_text().splitlines()]
start=next(row['stamp'] for row in rows if row.get('mission')=='RETURN_CORRIDOR')
source=(Path(__file__).with_name('pinpoint_headless_return_20261007.py')).read_text()
replacements={
    '825 <= r[\'stamp\'] <= 837':f'{start-10!r} <= r[\'stamp\'] <= {start+10!r}',
    '810 <= row[\'stamp\'] <= 850':f'{start-30!r} <= row[\'stamp\'] <= {start+30!r}',
    '825 <= stamp(r[\'data\']) <= 836':f'{start-10!r} <= stamp(r[\'data\']) <= {start+10!r}',
    '825 <= stamp(r[\'data\']) <= 835':f'{start-10!r} <= stamp(r[\'data\']) <= {start+10!r}',
    '831 <= r[\'row\'][\'t\'] <= 835':f'{start-2!r} <= r[\'row\'][\'t\'] <= {start+5!r}',
    "stamp(r['data']) >= 833.":f"stamp(r['data']) >= {start-1!r}",
    "maximum_horizontal_mps=max(math.hypot(r['data']['velocity']['x'],r['data']['velocity']['y']) for r in return_raw))":
    "maximum_horizontal_mps=max((math.hypot(r['data']['velocity']['x'],r['data']['velocity']['y']) for r in return_raw),default=0.))",
}
for before,after in replacements.items():
    assert source.count(before)==1,before
    source=source.replace(before,after)
target=Path(__file__).with_name('pinpoint_braked_navigation_return_20261007.py')
with target.open('x') as handle:handle.write(source)
print(json.dumps(dict(return_transition=start,diagnostic=str(target))))
