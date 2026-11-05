"""Preserve interrupted V32 offline failures and register explicit V33 scope."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v33_source_20261008'
new=json.loads((root/'.scratch/reduced_scope_v33_candidate_20261008/source_manifest.json').read_text())
old=json.loads((root/'.scratch/reduced_scope_v32_candidate_20261008/source_manifest.json').read_text())
p=json.loads((source/'provenance.json').read_text())
changed=[n for n in new if n in old and new[n]!=old[n]]
added=[n for n in new if n not in old]
assert changed==['sim/test_fail_closed_stages.py','scripts/run_tests.sh'] or set(changed)=={'sim/test_fail_closed_stages.py','scripts/run_tests.sh'},changed
assert set(added)=={'sim/qualification_offline_scope.py','sim/test_qualification_offline_scope.py'},added
assert all(new[n]==sha for n,sha in old.items() if n.startswith('src/'))
(source/'change_from_v32.json').write_text(json.dumps(dict(accepted_source=False,changed=changed,added=added,production_sources_unchanged=True,thresholds_unchanged=True,lidar_filter_unchanged=True,normal_response_s=.6,extra_queue_s=0.),indent=2))
log=root/'logs/reliability_reduced_v32_full_offline_20261008.log'
failure=dict(accepted=False,full_suite_pass=False,interrupted_for_diagnosis=True,failed=5,passed_before_interrupt=1085,log=str(log.relative_to(root)),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),deferred_strong_gust_failures=[
 'sim/test_corridor_stress.py::ShippedLaneStressTests::test_everything_at_once',
 'sim/test_corridor_stress.py::SplitLaneStressTests::test_gusty_crosswind',
 'sim/test_corridor_stress.py::SplitLaneStressTests::test_gusty_crosswind_with_dirty_lidar',
 'sim/test_corridor_stress.py::SplitLaneStressTests::test_gusty_crosswind_with_late_scans'],mean_wind_mps=8.,gust_mps=4.,in_scope_failed_test='sim/test_fail_closed_stages.py::FrontierSearchTests::test_red_lane_end_clips_the_lane_instead_of_dropping_it',in_scope_diagnosis='Per-tick hazard updates exhausted the finite fixture before enough distinct settled replans; cadence two ticks passes unchanged six-replan, zero-skip and full clear-lane coverage assertions',syntax_shell_config_frontend_pass=True,native_executed=False,campaign_executed=False)
f=root/'logs/reliability_reduced_scope_v32_source_20261008/interrupted_offline_failure_review.json'
with f.open('x') as stream:json.dump(failure,stream,indent=2)
head=f'''# Current checkpoint: V33 provisional, explicit reduced offline scope

V33 freezes {len(new)} controlled files, archive SHA256
{p['archive_sha256']}. All 121 combined focused checks pass.
Controller and perception source bytes are unchanged from V32. The changes
are the QR regression's hazard cadence and explicit offline scope/reporting.
Its original assertions remain: at least six replans, zero skipped lanes and
coverage of every clear lane part. The actual pytest collection checks prove
that five strong-gust positive flight tests are excluded while dirty lidar,
slow-airframe checks and the negative wind-fixture guard remain included.
Default offline runs still collect and execute every test without exclusions.

V32 passed all five targeted navigation cases, including field seeds 1/2/3,
with zero contacts/fence breaches and actual connected disarm. Random seed 4
retains DEGRADED visual-landing quality. Its exhaustive offline attempt was
interrupted for diagnosis: five failures and 1085 passes before interruption.
Four failures use mean wind 8 m/s, gust 4 m/s and are unresolved/deferred.
The fifth was the QR regression fixture timing. Python/shell syntax, config
parsing and frontend build passed. The original interrupted log, exact grades,
source archive, recordings and disarms are retained. No native or campaign
was executed on V32. No exhaustive offline pass is claimed.

Five targeted cases now rerun against the complete V33 freeze. The complete
reduced-scope offline suite follows, with five strong-gust flight tests
explicitly skipped and recorded, plus the three empty photograph corpus
skips. Neither exclusion is a pass. Five native 22/22 acceptances and the
96 eligible campaign flights remain pending. No accepted source exists.
Strong gusts and artificially delayed control remain unresolved and excluded.
The campaign retains 120 selected entries, 80 weather exclusions and 24
negative geometry classifications. No original 200-case qualification is
claimed. Acceptance thresholds and thin obstacles remain unchanged.

'''
for name in ('status.md','evidence_report_20261007.md'):
    f=base/name;s=f.read_text(encoding='utf-8')
    if '# Current checkpoint: V33 provisional' not in s:f.write_text(head+s,encoding='utf-8')
f=base/'evidence_report_20261007.md';s=f.read_text(encoding='utf-8')
if '| V32 exhaustive offline attempt |' not in s:
    s=s.replace('| Strong gust/delayed control |','| V32 exhaustive offline attempt | Interrupted: 5 failed, 1085 passed; four physical tests at mean 8 m/s/gust 4 m/s remain unresolved/deferred; QR fixture failed six-replan count, corrected cadence passes unchanged count/skip/coverage assertions; all five navigation flights passed/disarmed | Original failures preserved; never a full offline PASS; V33 explicit scope is unaccepted |\n| Strong gust/delayed control |',1)
    f.write_text(s,encoding='utf-8')
f=base/'evidence_index_20261007.json';index=json.loads(f.read_text())
index['current_continuation']=dict(source='V33 provisional',source_files=len(new),archive_sha256=p['archive_sha256'],remaining='Five V33 targeted trials, complete reduced-scope offline suite, five rendered acceptances, 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v33_targeted_20261008'];index['active_trial']=index['active_runs'][0]
index['accepted_source']=None;index['qualification_complete']=False
index['verification']['v32_interrupted_offline_failure_review']='logs/reliability_reduced_scope_v32_source_20261008/interrupted_offline_failure_review.json'
index['verification']['v33_focused']=dict(log='logs/reliability_v33_combined_focused_20261008.log',checks=121,accepted=False)
index['verification']['v33_frontier_timing_probe']='logs/reliability_frontier_hazard_schedule_probe_20261008.log'
f.write_text(json.dumps(index,indent=2),encoding='utf-8')
print('V33 provisional registered; all V32 failures and passes retained separately')
