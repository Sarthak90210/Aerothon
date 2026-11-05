"""Independent callback timing comparison for two closed navigation trials."""
import json,statistics
from pathlib import Path
root=Path(__file__).resolve().parents[2]
results=[]
for name in ('reliability_fast_planner_navigation_candidate_20261007',
             'reliability_live_clock_navigation_candidate_fixed_20261007'):
    out=root/'logs'/name/'my_world_calm_s1'
    samples=[json.loads(line) for line in (out/'onboard.jsonl').open()]
    corridor=[r['stamp'] for r in samples if r.get('mission')=='RETURN_CORRIDOR']
    timing=json.loads((out/'independent_command_receipt_timing.json').read_text())
    selected=[r for r in timing if min(corridor)-.3<=r['callback_sim_s']<=max(corridor)+.3]
    delays=sorted(r['callback_sim_s']-r['transmit_header_sim_s'] for r in selected)
    grade=json.loads((out/'navigation_grade.json').read_text())
    results.append(dict(run=name,packets=len(delays),return_interval_s=[min(corridor),max(corridor)],
        header_to_world_callback_median_s=statistics.median(delays),
        header_to_world_callback_p95_s=delays[min(len(delays)-1,int(.95*len(delays)))],
        header_to_world_callback_max_s=max(delays),
        separate_configured_physical_delay_s=.4,
        navigation_pass=grade['pass_navigation'],
        measured_corridor_clearance_m=grade['measured_corridor_clearance_m']))
report=dict(scope='Independent timing evaluation only; never controller input',cases=results,
    rendered_qualified=False,motor_delivery_qualified=False)
target=root/'logs/reliability_clock_navigation_timing_review_20261007.json'
with target.open('x') as h:json.dump(report,h,indent=2)
print(json.dumps(report,indent=2))
