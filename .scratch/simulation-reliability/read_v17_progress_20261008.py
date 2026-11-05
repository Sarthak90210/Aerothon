"""Compact read-only snapshots of the owned qualification jobs."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
for parent in [root/'logs/reliability_reduced_v17_targeted_20261008',root/'logs/reliability_reduced_v17_campaign_20261008']:
    if not parent.exists():continue
    for run in sorted(p for p in parent.iterdir() if p.is_dir()):
        onboard=run/'onboard.jsonl'
        if not onboard.exists():continue
        with onboard.open('rb') as f:
            f.seek(max(0,onboard.stat().st_size-200000));lines=f.read().splitlines()
        rows=[]
        for line in lines:
            try:rows.append(json.loads(line))
            except ValueError:pass
        if not rows:continue
        row=rows[-1];grade=run/'navigation_grade.json'
        status=dict(run=str(run.relative_to(root)),stamp=row.get('stamp'),phase=row.get('mission'),armed=row.get('flight',{}).get('data',{}).get('armed'))
        if grade.exists():
            try:
                g=json.loads(grade.read_text());status.update(navigation_pass=g['pass_navigation'],failures=[k for k,v in g['checks'].items() if not v])
            except ValueError:pass
        print(json.dumps(status))
for run in sorted((root/'logs').glob('reliability_reduced_v17_render_*_20261008')):
    summary=run/'summary.json'
    if summary.exists():
        try:
            s=json.loads(summary.read_text());print(json.dumps(dict(run=run.name,acceptance_pass=s['acceptance_pass'],failures=s['failures'],airborne_s=s['flight_time_s'])))
        except ValueError:pass
