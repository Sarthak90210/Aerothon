import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];docs=root/'.scratch/simulation-reliability'
current='''08 October reduced scope supersedes the original qualification target.
Strong-gust and artificially delayed-control work is deferred, unresolved,
and excluded; all existing failures remain archived. The original 200-case
campaign will not be claimed. Concrete weather filtering selects 120 of the
200 original world/preset/seed entries and excludes 80: mean wind >4 m/s
or gust >2 m/s, outside the existing moderate field preset. Exact selected
and excluded rows are in planned_campaign_scope.json. Feasibility auditing
may classify some selected entries without flight; such entries are not passes.

Normal mission startup now contains the camera-only clipped-bearing retry,
one bounded finer return sweep, measured-arrival gate braking, the native
zero-disturbance admission guard and independent native aircraft contact
grading. Aircraft geometry, mass, thin-obstacle filtering and clearance
thresholds remain unchanged. The contact recorder subscribes to actual
entity-scoped native channels, verifies publisher liveness, records skid
contacts and unsubscribes before teardown. The unarmed clean-shutdown smoke
passes with all seven vehicle channels, 25 native clock heartbeats and 258
contact rows; earlier topic and teardown failures are preserved.
Native contact grading requires a preflight skid-to-home-pad canary,
continuous publisher/clock coverage through flight, and no unexpected
vehicle contacts. Missing or malformed evidence fails qualification.

103 focused integration checks pass. Both ROS packages build and six installed
decision modules resolve to the exact root source; startup import hashes are
archived. The first reduced trial source c57104... inadvertently coupled
removal of the physical queue to an override of the controller timing model.
All three field seed trials failed (return/time, contacts in 1 and 2); they are
preserved, never qualification passes. V2 changes only the fixture setup:
physical extra queue 0 s, controller timing model unchanged at .4 s,
normal physical actuator response .6 s and computation budget .20 s.
The 909-file V2 archive SHA256 is
bc63e99f846ee8e3f712e8364ff22835855b7c992bd8d1b53e49ed06ad758966.
V2 field seeds 1/2/3 and the full native split acceptance are running in
parallel. No accepted final source exists. One final full offline suite,
all five rendered acceptances, the selected reduced campaign and final
accepted-source report remain pending; additional fixes will invalidate any
different-source passes. Detector rates from object-level trials are not
rendered perception qualification.
'''
p=docs/'status.md';old=p.read_text(encoding='utf8');p.write_text('# Current reduced qualification\n\n'+current+'\n## Prior checkpoints\n\n'+old,encoding='utf8')
with (docs/'evidence_report_20261007.md').open('a',encoding='utf8') as f:f.write('\n## Reduced scope, 08 October\n\n'+current)
p=docs/'evidence_index_20261007.json';index=json.loads(p.read_text(encoding='utf8'))
index.update(accepted_source=None,qualification_complete=False,campaign_200_qualified=False,
 reduced_scope=dict(selected_weather_cases=120,excluded_weather_cases=80,mean_wind_ceiling_mps=4,gust_ceiling_mps=2,artificial_transport_queue_s=0,normal_controller_timing_model_s=.4,physical_response_s=.6,computation_budget_s=.2,completed=False),
 deferred_unresolved=['strong-gust obstacle contacts','artificially delayed-control contacts and return-gate failures'],
 current_continuation=dict(source='logs/reliability_reduced_scope_v2_source_20261008',active=['field seeds 1/2/3, no injected queue','full native split 20261003'],full_offline_pending=True))
index['runs']['reduced first seed setup failures']=dict(path='logs/reliability_reduced_seed_trials_20261008',result=json.loads((root/'logs/reliability_reduced_seed_trials_20261008/report.json').read_text()),qualification_pass=False)
index['runs']['native vehicle contact clean shutdown smoke']=dict(path='logs/reliability_native_vehicle_contact_shutdown_20261007',scope='unarmed recording liveness only',result=json.loads((root/'logs/reliability_native_vehicle_contact_shutdown_20261007/smoke_review.json').read_text()),mission_qualification=False)
p.write_text(json.dumps(index,indent=2)+'\n',encoding='utf8')
for number in (37,38,39):
 p=next((docs/'issues').glob(f'{number}-*.md'))
 with p.open('a',encoding='utf8') as f:f.write('\n08 October reduced-scope instruction:\n'+current)
print('Reduced scope, failures and active source recorded; acceptance remains incomplete.')
