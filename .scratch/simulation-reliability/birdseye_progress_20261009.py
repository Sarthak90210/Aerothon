"""Compact passive status for the user-requested overhead recording."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
run = root/'logs/user_birdseye_split_v38_s20261003_retry3_20261009'
capture = root/'.scratch/birdseye_split_v38_20261009_retry3'
def tail(path):
    if not path.exists():
        return None
    with path.open('rb') as stream:
        stream.seek(max(0,path.stat().st_size-100000))
        lines=stream.read().splitlines()
    for line in reversed(lines):
        try:
            return json.loads(line)
        except ValueError:
            pass
    return None
row = tail(run/'onboard.jsonl') or {}
frame = tail(capture/'frames.jsonl') or {}
flight=row.get('flight',{}).get('data',{})
position=row.get('pose',{}).get('data',{}).get('pose',{}).get('position')
detail=row.get('avoidance',{})
print(json.dumps(dict(stamp=row.get('stamp'),phase=row.get('mission'),armed=flight.get('armed'),
    connected=flight.get('connected'),mode=flight.get('mode'),position=position,
    overhead_latest_stamp=frame.get('stamp'),overhead_frames=frame.get('index',-1)+1,
    avoidance=detail.get('state'),observed_clearance_m=detail.get('observed_clearance_m'),
    winch=row.get('winch',{}).get('state'),result=tail(run/'recorded_result.json'),
    recording_closed=(capture/'capture_summary.json').exists(),qualification='paused')))
