import hashlib,json,shutil,sys
from pathlib import Path
root=Path.cwd();base=root/'.scratch/simulation-reliability'
prior=base/'evidence_report_20261007_prior_20261008.md'
if not prior.exists():shutil.copy2(base/'evidence_report_20261007.md',prior)
index_path=base/'evidence_index_20261007.json';index=json.loads(index_path.read_text(encoding='utf-8'))
index['active_runs']=['logs/reliability_reduced_v10_targeted_20261008/my_world_field_s1','logs/reliability_reduced_v10_targeted_20261008/my_world_random_s3']
index['current_continuation']=dict(source='V10 provisional',source_files=914,archive_sha256='4ae04641a3a81a36e4e2dd5b0da00aa712e87d03a842340d2df86e411265bd45',targeted_runner='logs/reliability_reduced_v10_targeted_20261008',remaining='Remaining targeted navigation, one final full offline suite, five same-source rendered acceptances, reduced campaign and accepted-source report')
index['runs']['V9 targeted turn hold diagnostic']=dict(path='logs/reliability_reduced_v9_targeted_20261008',scope='object navigation; no motor delivery or rendered qualification',result=json.loads((root/'logs/reliability_reduced_v9_targeted_20261008/report.json').read_text()))
index_path.write_text(json.dumps(index,indent=2),encoding='utf-8')
report='''# Reduced-scope qualification evidence — incomplete

Accepted source: **none**. Reduced-scope qualification has not passed. The
original 200-case qualification is not claimed. Strong-gust and artificially
delayed-control failures remain unresolved and excluded by the user's instruction.

The active provisional source is V10: 914 controlled files, archive SHA256
`4ae04641a3a81a36e4e2dd5b0da00aa712e87d03a842340d2df86e411265bd45`.
The archive and manifest are in `logs/reliability_reduced_scope_v10_source_20261008`.
Field seed 1 and retained random seed 3 are active in
`logs/reliability_reduced_v10_targeted_20261008`. No earlier source is accepted
as qualification for this implementation.

## Scope and configuration

The original matrix has 10 worlds × 4 weather presets × 5 seeds = 200 entries.
The existing moderate field envelope is mean wind ≤4 m/s and gust ≤2 m/s.
Calm and field retain 50 entries each; concrete random seeds 3 and 4 retain
20. Worst weather excludes 50; random seeds 1, 2 and 5 exclude another 30.
Thus **120 selected entries and 80 weather exclusions**.

Existing geometry checks classify 12 selected `editor_test` entries as invalid
and 12 `my_world_offaxis` entries as infeasible at the required clearance.
These are preserved negative classifications, never traversal passes. The
remaining **96 eligible flights** span eight valid worlds. Executed reduced
campaign flights: **zero**. Exact rows and reasons are in
`logs/reliability_reduced_scope_v8_source_20261008/planned_geometry_scope.json`.

Object-navigation trials use RTF2, no added transport queue, calibrated zero
extra queue in the controller model, unchanged .6 s physical actuator response,
normal controller callbacks and .20 s computation budget. Native mission startup
retains its normal timing and actuator defaults. Object fixtures cannot qualify
rendered vision, motor delivery, or video capture. Full native acceptance must
use normal mission startup, the calibrated delivery profile and actual FCU disarm.

## Current fixes and checks

Normal startup integrates camera capture scheduling, perception, measured-arrival
gate braking, bounded camera-only return framing and the motion admission guard.
The motion certificate batches exactly the same sampled trajectory points.
The 104-segment benchmark measured 6.332 ms versus 1.159 ms median, 5.465× faster;
its 160-path equivalence test includes retained thin obstacle observations.

The search guard checks the current position intent rather than an obsolete
preview. V8 repeatedly braked its own completed hold. V9 allowed a single handoff
but then interrupted stationary turns. Real command-getter and leaf regressions
reproduced both. V10 keeps an exact completed hold eligible only while fresh
settled-motion evidence remains valid, clears that eligibility for any replacement
position command, and restarts the turn anchor from the measured stop position.
The focused search/router set passes **66** checks. Unsafe replacement commands,
stale observations, distinct settled samples and the certified escape are covered.

Required thresholds remain .70 m corridor clearance, 1.50 m restricted-zone
clearance, 900 s airborne, complete camera evidence, independent aircraft contacts,
qualified delivery and actual connected FCU disarm. No wider lidar filter is used.

## Closed evidence and remaining failures

| Evidence | Result | Qualification limit |
|---|---|---|
| V3 fields 1/2/3 | All 13 navigation checks passed; actual disarm; zero contacts/fence | Different source; object navigation only |
| V3 offline | 1477 passed, 3 skipped; syntax/configuration/frontend passed | Different source; final suite still pending |
| V3 native split, 20261003 | 21/22; completed, motor delivery and actual disarm; .717815 m clearance | Aircraft-contact check failed; 215 lowered-jaw target-floor contact pairs |
| V5 field 3, RTF4 | Failed corridor clearance .619442 m after .36 s certificate exceeded .20 s budget | Preserved failure |
| Exact V5 field 3, RTF2 | All 13 navigation checks passed | Different source; no rendered qualification |
| V7 retained random 4 | All 13 navigation checks passed | Different source |
| V7 retained random 3 | Failed; QR search lasted 799.6 s before return; battery RTL | Remains in scope |
| V8 fields 1/2/3 and random 3/4 | All five failed in battery RTL; connected disarm verified | Completed-hold braking deadlock; archived failures |
| V9 field 1 | All 13 navigation checks passed; zero contacts/fence; disarmed, 845.1 s total sim | Different source; no delivery qualification |
| V9 retained random 3 | Failed QR time/return/mode/ceiling/red-clearance checks; recorded operator RTL and disarm | Remains in scope; turn holds repeatedly interrupted |
| Strong gust/delayed control | Preserved obstacle contacts and other failures | Deferred, unresolved, excluded |

The passive native contact recorder covers all seven vehicle contact channels,
checks publisher/clock coverage through disarm, and requires a preflight skid
canary. New evidence includes actual contact positions and fresh winch receipt
timestamps. Intended lowered-hook contact with the target floor is classified
only with fresh onboard winch/mission state, fresh independent elevated aircraft
pose, and actual surface contact positions on the target. Airframe obstacle,
wall, stowed-hook, off-target, missing-position and stale-evidence contacts fail.
V3 lacks the new measurements and remains failed; it is not retroactively passed.

V3 split detector evidence: camera 2808 distinct captures, 5.0246 captures/s in
sim time and 1.1511 delivered/s on the host. Search QR 19.1074 captures/s sim,
4.4936 delivered/s host, .234 s p95 sim latency; red 19.0909 captures/s sim,
4.4897 delivered/s host, .232 s p95 sim latency. These rates describe that failed
run and cannot establish current-source rendered qualification.

All earlier diagnostic outcomes, recordings and telemetry remain available via
`evidence_index_20261007.json` and the unchanged historical report
`evidence_report_20261007_prior_20261008.md`. Closed per-run reviews store source,
configuration and artifact hashes. Every prior failure retains its original grade.

## Work still required

Complete all three field seeds and retained mild-weather regressions on one final
source. Then run one final full offline suite, five full rendered acceptances
(standard 20261003 and 1001; shipped, rotated and split 20261003), and the 96-flight
reduced campaign with 24 negative geometry classifications and 80 explicit weather
exclusions. Populate accepted source hashes, per-run detector rates, recordings,
telemetry and exact outcomes only after those checks close. Until then this report
and the machine index both explicitly remain incomplete.
'''
(base/'evidence_report_20261007.md').write_text(report,encoding='utf-8')
status=base/'status.md';old=status.read_text(encoding='utf-8')
status.write_text('''# Current checkpoint — V10 provisional

No accepted final source. V10 is frozen at 914 files, archive SHA256
4ae04641a3a81a36e4e2dd5b0da00aa712e87d03a842340d2df86e411265bd45.
Field 1 and retained random 3 are active. Search/router regressions pass 66,
including stationary turns after braking. V9 field 1 passed navigation;
random 3 failed and was safely stopped through recorded RTL and actual disarm.
Strong-gust/delay failures remain unresolved/excluded. Final offline, all five
rendered acceptances and reduced campaign remain pending. See the consolidated
evidence report for the current state and exact 96/24/80 scope.

## Prior checkpoints

'''+old,encoding='utf-8')
print('Consolidated report and index updated; qualification explicitly incomplete')
