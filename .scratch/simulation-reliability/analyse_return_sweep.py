"""Summarise real return-stage yaw commands and camera changes."""
import json, math, sys
from pathlib import Path

out = Path(sys.argv[1])
rows = [json.loads(x) for x in (out/'onboard.jsonl').open()]
rr = [r for r in rows if r.get('mission') == 'RETURN_GATE_SEARCH']
start, end = rr[0]['stamp'], rr[-1]['stamp']
prev = None
total = 0.0
for line in (out/'flight_commands.jsonl').open():
    r = json.loads(line)
    if not start <= r['stamp'] <= end or r['topic'] != '/mavros/setpoint_position/local':
        continue
    q = r['data']['pose']['orientation']
    yaw = math.atan2(2*(q['w']*q['z']+q['x']*q['y']), 1-2*(q['y']**2+q['z']**2))
    p = r['data']['pose']['position']
    if prev is not None:
        delta = abs(math.atan2(math.sin(yaw-prev), math.cos(yaw-prev)))
        if delta < .01:
            continue
        total += delta
    prev = yaw
    print(round(r['stamp'],3), 'yaw', round(math.degrees(yaw),1),
          'position', [round(p[k],2) for k in ('x','y','z')])
print('Total requested shortest yaw travel (degrees):', round(math.degrees(total),1))
