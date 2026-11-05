"""Compact passive telemetry status; never an acceptance decision."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
for run in sorted((root / 'logs').glob('reliability_reduced_v38_render_*_20261008')):
    path = run / 'onboard.jsonl'
    if not path.exists():
        continue
    with path.open('rb') as stream:
        stream.seek(max(0, path.stat().st_size - 100000))
        lines = stream.read().splitlines()
    rows = []
    for line in lines:
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    if not rows:
        continue
    row = rows[-1]
    pose = row.get('pose', {}).get('data', {}).get('pose', {}).get('position')
    print(json.dumps(dict(run=run.name, stamp=row['stamp'], mission=row.get('mission'),
        flight=row.get('flight', {}).get('data'), pose=pose,
        winch=row.get('winch'), camera=row.get('camera_state'),
        banner=row.get('banner_detail'), qr=row.get('qr_timing'),
        red=row.get('red_timing'), avoidance=row.get('avoidance')), separators=(',', ':')))
