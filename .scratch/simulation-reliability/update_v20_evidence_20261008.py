"""Archive the landing startup diagnosis and current unaccepted candidate."""
import csv,hashlib,json,math,re
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
run=root/'logs/reliability_reduced_v19_targeted_20261008/my_world_field_s2'
track=list(csv.DictReader((run/'evaluation_truth_track.csv').open()))
first_land=next(row for row in track if row['mode']=='LAND')
log=(run/'stack.log').read_text()
relevant=[line for line in log.splitlines() if any(term in line for term in
    ['precision descent:','landing PRECISE','Mission state -> CAMERA_NADIR'])]
diagnosis=dict(hypotheses=[
    'Returning below the tracking floor makes precision descent commit before visual acquisition',
    'Estimator drift during LAND moves the latched estimated position',
    'Stale or banked QR offsets corrupt the corrected-home calculation'],
    first_native_fixture_land_sample=first_land,
    distance_at_first_land_m=math.hypot(float(first_land['x']),float(first_land['y'])),
    final_home_distance_m=json.loads((run/'navigation_grade.json').read_text())['full_grade']['landed_from_home_m'],
    relevant_logs=relevant,actual_tree_red='logs/reliability_v20_landing_startup_height_red_20261008.log',
    focused_green='logs/reliability_v20_landing_startup_height_green_20261008.log',
    before=dict(home_command_alt_m=5.,tracking_floor_m=6.983935839901704,
                computed_acquisition_alt_m=8.483935839901704),
    candidate='V20 wires GotoHome to the actual PrecisionDescent.start_alt; same marker/lens parameters, thresholds and physical response',
    accepted_source=False,files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        for p in [run/'stack.log',run/'evaluation_truth_track.csv',run/'onboard.jsonl',run/'navigation_grade.json']})
(run/'landing_startup_height_diagnosis.json').write_text(json.dumps(diagnosis,indent=2))
source=root/'logs/reliability_reduced_scope_v20_source_20261008'
prov=json.loads((source/'provenance.json').read_text());sha=prov['archive_sha256']
old=json.loads((root/'.scratch/reduced_scope_v19_candidate_20261008/source_manifest.json').read_text())
new=json.loads((root/'.scratch/reduced_scope_v20_candidate_20261008/source_manifest.json').read_text())
changes=dict(added=[name for name in new if name not in old],removed=[name for name in old if name not in new],
    changed=[name for name in new if name in old and new[name]!=old[name]],
    thresholds_unchanged=True,normal_actuators_unchanged=True,lidar_filter_unchanged=True,accepted_source=False)
(source/'change_from_v19.json').write_text(json.dumps(changes,indent=2))
headline=f'''# Current checkpoint — V20 provisional

No accepted source. Frozen {len(new)} files; archive SHA256
{sha}.
All 11 normal-startup module imports match this freeze. V19 passed return,
QR search, clearance and time checks for all five targeted cases; fields 1/3
and mild random 4 passed navigation, while field 2 and mild random 3 failed
home landing at 1.67/2.19 m. All five actually disarmed; no contacts/fence breaches.
Those failed grades are closed and preserved, not upgraded.
The actual flown tree commanded 5 m home altitude although its own landing
leaf required 8.48 m for acquisition and 6.98 m for tracking. It immediately
committed below the tracking floor without observing the home marker.
The real built-tree regression failed; V20 wires home return to the existing
derived landing acquisition altitude. 230 focused startup/landing/routing
checks pass. Return framing, perception, normal timing, actuator response and
all acceptance thresholds are unchanged from V19.
Two-worker V20 targeted trials are active, with retained mild random 3 and
field 2 first. Final offline, all five native rendered acceptances and 96
eligible campaign flights remain pending. 24 invalid/infeasible geometry
classifications and 80 excluded weather cases are not passes; no original
200-case qualification is claimed. Strong gusts and artificial control delay
remain unresolved and excluded. All failures and recordings remain preserved.

'''
p=base/'status.md';text=p.read_text(encoding='utf-8')
if not text.startswith('# Current checkpoint — V20 provisional'):
    p.write_text(headline+'## Prior checkpoints\n\n'+text,encoding='utf-8')
p=base/'evidence_report_20261007.md';text=p.read_text(encoding='utf-8')
section=f'''## Current provisional V20

No accepted source. V20 freezes {len(new)} controlled files, archive SHA256
`{sha}`. All 11 normal-startup imports match. Two-worker targeted trials are
active, with retained mild random 3 and field 2 first. The final offline suite,
five full native acceptances and 96 campaign flights remain gated.

V19 closed 3/5 navigation passes: field 1, field 3 and mild random 4. All five
passed QR search, both corridor traversals, .70 m clearance and the 900 s limit.
Field 2 and mild random 3 failed only home landing (1.67 and 2.19 m), with actual
disarm and zero contacts/fence breaches. Mild random 3 flew 890.5 airborne seconds
with .726310539 m corridor clearance; it remains a failed navigation result.
Original payload grades remain unqualified. The full per-artifact closure is
`logs/reliability_reduced_scope_v19_source_20261008/targeted_failure_closed_review.json`.

The normal built tree returned at 5 m while the landing leaf calculated 6.98 m
tracking floor and 8.48 m acquisition altitude. Its first tick immediately
committed without visual acquisition. The actual built-tree regression failed.
V20 commands the already-derived acquisition altitude before descent; 230 focused
checks pass. The landing diagnosis, commands and independent fixture track are
archived in `logs/reliability_reduced_v19_targeted_20261008/my_world_field_s2/landing_startup_height_diagnosis.json`.
The change does not alter LAND physics, aircraft actuator timing, perception,
return framing, lidar filtering or grading thresholds. No V19 pass is reused as
V20 qualification. Reduced scope remains 120 selected, 96 eligible flights,
24 negative geometry classifications and 80 weather exclusions; zero campaign
flights have executed. Strong-gust and artificial-delay failures remain excluded
and unresolved.

## Prior provisional V19

'''
if '## Current provisional V20' not in text:
    text=text.replace('## Current provisional V19\n\n',section,1)
    text=text.replace('Finish the five targeted navigation cases and final offline suite on V19, then',
                      'Finish the five targeted navigation cases and final offline suite on V20, then')
    text=text.replace('| Strong gust/delayed control |',
        '| V19 field 2 | Return/time/clearance passed; home landing failed at 1.67 m; actual disarm | Preserved failure; remains in scope |\n'
        '| V19 retained random 3 | Return/time/clearance passed; home landing failed at 2.19 m; actual disarm | Preserved failure; landing startup mismatch reproduced |\n'
        '| Strong gust/delayed control |',1)
    p.write_text(text,encoding='utf-8')
p=base/'evidence_index_20261007.json';idx=json.loads(p.read_text(encoding='utf-8'))
idx['current_continuation']=dict(source='V20 provisional',source_files=len(new),archive_sha256=sha,
    remaining='Five targeted navigation trials, final offline suite, five full native rendered acceptances and 96 eligible campaign flights')
idx['active_runs']=['logs/reliability_reduced_v20_targeted_20261008']
idx['reduced_scope']['classification_audit']='logs/reliability_reduced_scope_v20_source_20261008/planned_geometry_scope.json'
idx['verification'].update(
    v19_targeted_failure_closed_review='logs/reliability_reduced_scope_v19_source_20261008/targeted_failure_closed_review.json',
    v19_landing_startup_diagnosis='logs/reliability_reduced_v19_targeted_20261008/my_world_field_s2/landing_startup_height_diagnosis.json',
    v20_installed_startup='logs/reliability_reduced_scope_v20_source_20261008/installed_startup_imports.json',
    v20_landing_focused='logs/reliability_v20_landing_startup_height_green_20261008.log')
idx['accepted_source']=None;idx['qualification_complete']=False;idx['campaign_200_qualified']=False
p.write_text(json.dumps(idx,indent=2),encoding='utf-8')
print(json.dumps(changes))
