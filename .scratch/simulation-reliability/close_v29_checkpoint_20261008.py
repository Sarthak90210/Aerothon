"""Preserve failed timing trials and explicitly mark all qualification pending."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
report=json.loads((root/'logs/reliability_reduced_v29_targeted_20261008/report.json').read_text())
head='''# Current checkpoint: V29 closed, timing failures unresolved

V29 executed three of five planned targeted navigation trials. Field seed 2
passed all navigation checks and actually disarmed at 776.60 s, with DEGRADED
visual landing quality. Mild random seed 3 and field seed 3 failed the
unchanged 900-second limit; both safely returned and actually disarmed.
All three recorded zero obstacle contacts and zero geofence breaches. Mild
seed 3 passed both corridors with .7230623482323127 m minimum clearance.
Two unflown trials were cancelled, never counted as passes. The original
failed results and all telemetry remain archived. No full suite, rendered
acceptance or campaign was run on V29. No accepted source exists.

Landing diagnosis is active. A simplified free-airframe replay finished in
10.79 s and does not reproduce the full timing failure. Replaying recorded
aircraft positions reproduces the long camera outage but cannot verify a
counterfactual controller change. A separate actual PrecisionDescent regression
does reproduce early climb toward the stale initial home-marker fix after
one missing camera result, before the existing loss grace expires. The first
candidate correction retains the latest visual horizontal target during
that existing grace while holding current height. It does not continue
descent without lock or change the prolonged-loss recovery, timeout or any
acceptance threshold. Whole-flight verification is required before adoption.

Strong-gust and artificially delayed-control failures remain unresolved,
preserved and excluded. Reduced scope remains 120 weather-selected cases,
80 weather exclusions and 24 negative geometry classifications, leaving 96
eligible campaign flights. None has qualified; original 200-case qualification
is not claimed.

'''
for name in ['status.md','evidence_report_20261007.md']:
 f=base/name;s=f.read_text(encoding='utf-8')
 if '# Current checkpoint: V29 closed' not in s:f.write_text(head+s,encoding='utf-8')
f=base/'evidence_index_20261007.json';index=json.loads(f.read_text(encoding='utf-8'))
index['accepted_source']=None;index['qualification_complete']=False;index['active_runs']=[];index['active_trial']=None
index['current_continuation']=dict(source='V29 closed; landing correction pending verification',targeted=report,remaining='Targeted timing fixes, final offline suite, five rendered acceptances, 96 eligible campaign flights')
index['verification']['v29_closed_failure_review']='logs/reliability_reduced_scope_v29_source_20261008/targeted_failure_closed_review.json'
f.write_text(json.dumps(index,indent=2),encoding='utf-8')
print('V29 closed failures recorded; no qualification claim')
