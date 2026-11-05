"""Offline focused qualification, explicitly separate from full acceptance."""
import json
import sys
from bisect import bisect_right
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'sim'))
from campaign_record import navigation_grade
from check_track import traversal
out=Path(sys.argv[1])
track=json.loads((out/'evaluation_track.json').read_text())
driver=[json.loads(line) for line in (out/'trial_driver.jsonl').read_text().splitlines()]
times=[r['stamp'] for r in driver]
# The standby mission node also publishes WAITING during this operator trial.
# Use the actual driver's recorded commands for phase assignment, retaining
# every native aircraft sample and leaving the original evidence untouched.
aligned=[]
for row in track:
    i=bisect_right(times,row['t'])-1
    aligned.append({**row,'state':driver[i]['phase'] if i>=0 else 'SETUP_WAIT'})
track=aligned
layout=json.loads((out/'layout.json').read_text())
nav=[r for r in track if r['state'] in ('CROSS_GATE','SETTLE_ENTRY','RETURN_CORRIDOR')]
# Keep approach, descent, crossing, recovery and landing samples in the physical clearance check.
grade=navigation_grade(track,layout,'b')
traversed,_=traversal(nav,layout,0,outbound=False)
result=json.loads((out/'trial_result.json').read_text())
checks={'rendered return trial completed':result['state']=='TRIAL_COMPLETE',
        'disarmed at trial end':result['final_armed'] is False,
        'independent return samples recorded':len(nav)>100,
        'navigation-time input isolation audit passed':
            (out/'decision_inputs_navigation.json').exists() and
            json.loads((out/'decision_inputs_navigation.json').read_text()).get('pass') is True,
        'corridor clearance at least 0.70 m':grade['checks']['corridor clearance at least 0.70 m'],
        'full return lane traversed below walls':traversed.get('found',False) and not traversed.get('n_bad')}
summary=dict(focused_pass=all(checks.values()),checks=checks,
    handover_mode=json.loads((out/'configuration.json').read_text()).get('handover_mode','stationary'),
    clearance_phase_source='all recorded native aircraft samples, including operator approach',
    measured_corridor_clearance_m=grade['measured_corridor_clearance_m'],
    full_mission_qualified=False,rendered_search_qualified=False,motor_delivery_qualified=False,
    phase_source='timestamped operator trial commands aligned to native aircraft samples',
    note='Starting fixture comes from a recorded FCU pose. This trial omits perception gate finding, search and delivery.')
summary_path=out/(sys.argv[2] if len(sys.argv)>2 else 'focused_summary.json')
if summary_path.exists():raise SystemExit('Focused summary already exists; preserve it and select a new filename')
summary_path.write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
raise SystemExit(0 if summary['focused_pass'] else 1)
