"""Independent offline grade of a rendered motor-priority observer trial."""
import json
import math
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src/aerothon_mission/mission_bt'))
sys.path.insert(0,str(ROOT/'src/aerothon_sim/sim_gazebo'))
from mission_bt.delivery_observer import stable
from sim_gazebo.contact_release import surface_contact
out=Path(sys.argv[1])
def rows(name):
    return [json.loads(line) for line in (out/name).read_text().splitlines() if line.strip()]
result=json.loads((out/'driver/result.json').read_text())
trace=rows('driver/onboard.jsonl')
done=next((r for r in trace if (r.get('observation') or {}).get('state')=='DONE'),None)
probes=[r for r in trace if (r.get('observation') or {}).get('state') in ('PROBE','CANDIDATE_PROBE','PROBE_HOLD','STOW','FINAL','DONE')]
start=probes[0]['stamp'] if probes else math.inf
finish=done['stamp'] if done else start
payload=[r for r in rows('evaluation_truth.jsonl') if start<=r['stamp']<=finish]
displacement=max((math.dist((payload[0]['x'],payload[0]['y'],payload[0]['z']),
                           (r['x'],r['y'],r['z'])) for r in payload),default=math.inf)
height=max((r['z'] for r in payload),default=math.inf)
contacts=rows('evaluation_contacts.jsonl')
ground=[r for r in contacts if any(surface_contact(c['collision1'],c['collision2'])
                                 for c in r['contacts'])]
profile=json.loads((out/'frozen_calibration.json').read_text())
ceiling=(profile['loaded_mean']-3*profile['loaded_std']+
         profile['unloaded_mean']+3*profile['unloaded_std'])/2
telemetry=(done or {}).get('telemetry')
checks={
    'observer confirmed actual rendered delivery':result.get('status')=='DONE' and result.get('delivery_confirmed') is True,
    'touchdown and detachment inferred separately':result.get('touchdown_inferred') is True and result.get('detachment_inferred') is True,
    'stable fresh unloaded FCU observation at confirmation':bool(done and stable(telemetry,done['stamp']) and telemetry['effort']<ceiling),
    'full hook stow estimate before confirmation':bool(done and done['winch']['payout_estimate_m']<=.02),
    'independent payload contact precedes inference':bool(ground and ground[0]['stamp']<=finish),
    'payload remains supported through probe and stow':len(payload)>20 and displacement<=.15 and height<=.20,
    'disarmed at trial end':result.get('final_armed') is False,
    'camera recording exists':(out/'onboard_sim_time.mp4').is_file(),
    'decision input audit excludes simulator truth':json.loads((out/'decision_inputs.json').read_text()).get('pass') is True,
    'active delivery driver input audit passed':(out/'decision_inputs_delivery.json').exists() and
        json.loads((out/'decision_inputs_delivery.json').read_text()).get('pass') is True,
}
summary=dict(focused_pass=all(checks.values()),checks=checks,
    payload_displacement_during_probe_m=displacement,max_payload_height_during_probe_m=height,
    motor_unloaded_ceiling=ceiling,full_mission_qualified=False,
    rendered_search_qualified=False,return_corridor_qualified=False,
    note='Evaluation truth is read only after the trial. Aircraft decisions use onboard observations.')
summary_path=out/(sys.argv[2] if len(sys.argv)>2 else 'focused_summary.json')
if summary_path.exists():raise SystemExit('Focused summary already exists; select a new filename')
summary_path.write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
raise SystemExit(0 if summary['focused_pass'] else 1)
