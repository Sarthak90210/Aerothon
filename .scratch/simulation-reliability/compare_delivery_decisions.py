"""Post-flight comparison only. Native truth never enters drone decisions."""
import json, math, sys
from pathlib import Path

out = Path(sys.argv[1])
rows = [json.loads(x) for x in (out/'onboard.jsonl').open()]
active = [r for r in rows if r.get('mission') == 'WINCH_DROP'
          and isinstance(r.get('observation'), dict)]
events = []
previous = None
for r in active:
    o = r['observation']
    key = (o.get('state'), o.get('attempt'), o.get('touchdown_inferred'),
           o.get('detachment_inferred'))
    if key != previous:
        events.append(dict(recorded_stamp=r['stamp'], **o))
        previous = key
contacts = [json.loads(x) for x in (out/'evaluation_contacts.jsonl').open()]
ground = next((r['stamp'] for r in contacts if any(
    'delivery_zone' in c.get('collision2','') or 'ground' in c.get('collision2','')
    or 'delivery_zone' in c.get('collision1','') or 'ground' in c.get('collision1','')
    for c in r.get('contacts', []))), None)
probe = next((r['stamp'] for r in active if r['observation'].get('state')
              in ('PROBE', 'CANDIDATE_PROBE')), None)
done = next((r for r in active if r['observation'].get('state') == 'DONE'), None)
native = [json.loads(x) for x in (out/'evaluation_truth.jsonl').open()]
support = [r for r in native if probe is not None and done is not None
           and probe <= r['stamp'] <= done['stamp']]
movement = max((math.dist([r[k] for k in ('x','y','z')],
                         [support[0][k] for k in ('x','y','z')])
                for r in support), default=None)
report = dict(source='post-flight independent evaluation; no drone input',
              first_native_ground_contact_stamp=ground, events=events,
              probe_to_done_native_samples=len(support),
              maximum_native_payload_movement_m=movement,
              full_mission_acceptance=json.loads((out/'summary.json').read_text())['acceptance_pass'])
dest = out/'delivery_decision_comparison.json'
if dest.exists():
    raise SystemExit('Comparison already exists; original report preserved')
dest.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(dict(ground_contact_stamp=ground,probe_stamp=probe,
                     confirmation_stamp=done['observation']['stamp'] if done else None,
                     payload_movement_m=movement,native_samples=len(support)), indent=2))
