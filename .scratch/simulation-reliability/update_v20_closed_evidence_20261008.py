"""Keep original failures and distinguish fixture navigation from delivery."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
parent=root/'logs/reliability_reduced_v20_targeted_20261008'
report=json.loads((parent/'report.json').read_text())
summary=[]
for r in report['results']:
    run=parent/r['run'];g=json.loads((run/'navigation_grade.json').read_text())
    summary.append(dict(run=r['run'],pass_navigation=r['navigation_pass'],failures=r['navigation_failures'],
        corridor_clearance_m=g['measured_corridor_clearance_m'],airborne_s=g['full_grade']['flight_time_s'],
        home_m=g['full_grade']['landed_from_home_m'],actual_disarm=not g['full_grade']['final_armed']))
text='''## V20 closed result

V20 is unaccepted. Fields 1, 2 and 3 and mild random seed 4 passed all 13
navigation checks. Mild random seed 3 exceeded 900 seconds and was safely
returned by the watchdog; its original time and unexpected-mode failures
remain failed. All five actually disarmed, with zero contacts or fence breaches.
Field 2 and mild random 4 reported degraded precision landing; their navigation
checks passed but this quality limitation is preserved. Fixture payload delivery
remains unmeasured and no motor delivery qualification is claimed.

The mild seed 3 search occupied simulated seconds 717.57 to 817.20. A whole
green region near the later orbit lead was visible in recorded snapshots by
724.13, but the orbit began after both complete sweeps. Snapshot green replay
uses the recorded pose and no lidar and is an approximate diagnostic, not a
complete 20 Hz identity history. The landing physics probe passed before any
new landing change, achieving visual lock in 8.6 seconds; it did not reproduce
the field seed 2 precision timeout. No landing metric change followed it.

Exact source, configuration, original grades, videos, telemetry and connected
disarm are closed in
`logs/reliability_reduced_scope_v20_source_20261008/targeted_failure_closed_review.json`.
The search diagnosis is
`logs/reliability_reduced_v20_targeted_20261008/my_world_random_s3/return_search_latency_diagnosis.json`.
Final offline, all five native rendered acceptances and the 96 eligible campaign
flights remain pending. Scope stays 120 selected, 24 negative geometry
classifications and 80 excluded weather cases. Strong gust and artificial delay
remain unresolved; original 200-case qualification is not claimed.

'''
for name in ['status.md','evidence_report_20261007.md']:
    p=base/name;s=p.read_text(encoding='utf-8')
    if '## V20 closed result' not in s:p.write_text(text+s,encoding='utf-8')
p=base/'evidence_index_20261007.json';index=json.loads(p.read_text())
index.setdefault('verification',{})['v20_closed_targeted']=dict(path='logs/reliability_reduced_scope_v20_source_20261008/targeted_failure_closed_review.json',results=summary,accepted=False)
index['active_trial']=None;index['accepted_source']=None;index['qualification_complete']=False
p.write_text(json.dumps(index,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
