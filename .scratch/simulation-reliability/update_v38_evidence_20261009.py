"""Record final UI/fixture correction without adopting older source passes."""
import ast,hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v38_source_20261008'
new=json.loads((root/'.scratch/reduced_scope_v38_candidate_20261008/source_manifest.json').read_text())
old=json.loads((root/'.scratch/reduced_scope_v37_candidate_20261008/source_manifest.json').read_text())
p=json.loads((source/'provenance.json').read_text());changed=[n for n in new if n in old and new[n]!=old[n]]
assert changed==['src/aerothon_mission/mission_bt/mission_bt/mission_tree.py','sim/test_search_current_command.py'],changed
assert set(new)==set(old)
def control_tree(path):
 tree=ast.parse(path.read_text(encoding='utf-8'))
 tree.body=[n for n in tree.body if not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='STATE_NAMES' for t in n.targets))]
 return ast.dump(tree,include_attributes=False)
name=changed[0];assert control_tree(root/name)==control_tree(root/'.scratch/reduced_scope_v37_candidate_20261008'/name)
(source/'change_from_v37.json').write_text(json.dumps(dict(accepted_source=False,changed=changed,added=[],focused_checks=152,flight_logic_ast_unchanged=True,ui_stage_registered='CameraBannerReturnAlignment -> CAMERA_BANNER',fixture_correction='Completed holds at x9..9.1 now outside the toy observed red margin; travel x30 still intersects red. Every original assertion retained. Two new real-command controls preserve original inside-margin refusal and distinct-capture escape handoff.',thresholds_unchanged=True,lidar_filter_unchanged=True,headless_rtf=1.,normal_response_s=.6,extra_queue_s=0.,records={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['logs/reliability_v37_state_map_red_20261009.log','logs/reliability_v37_search_hold_fixture_probe_20261009.log','logs/reliability_v38_integrated_focused_20261009.log','logs/reliability_reduced_scope_v37_source_20261008/failed_full_offline_closed_review.json']}),indent=2))
head=f'''# Current checkpoint: V38 provisional, complete offline integration correction

V38 freezes {len(new)} controlled files, archive SHA256
{p['archive_sha256']}. 152 integrated focused checks pass.
The camera settlement stage now has its normal CAMERA_BANNER UI state.
Flight-logic AST is unchanged after excluding only STATE_NAMES. Seven
stationary-hold fixtures previously placed their expected stopped poses
inside the observed 1.50 m red margin. The toy boundary now puts those
stops outside that unchanged margin; the requested trip still crosses
red. Every original assertion is retained. Two additional actual-command
controls require an inside-margin stop to keep escaping and require
distinct fresh captures after actual certified escape arrival. Existing
observed-exclusion, actual gate/vertical physics, camera handoff, stale
motion, braking, landing and scan-registration regressions also pass.
No world geometry, filtering, acceptance threshold or flight policy changed.

V37's five navigation passes remain archived on their original source.
Its complete reduced offline suite FAILED eight checks: one UI-state
mapping and seven invalid stationary-hold fixtures; 1687 passed, eight
skipped, with syntax/configuration and frontend checks passing. The exact
source, failure names, complete log and hashes are preserved in
failed_full_offline_closed_review.json. They are not counted as V38 passes.
No native acceptance or campaign ran on V37.

V38 runs all five targeted flights again on the final source and exact
RTF1 configuration, then one complete reduced-scope offline suite, five
native 22/22 acceptances and 96 eligible campaign flights. Strong gusts and
artificial delayed control remain unresolved and excluded. No source is
accepted yet, and no original 200-case qualification is claimed.

'''
for name in ['status.md','evidence_report_20261007.md']:
 f=base/name;s=f.read_text(encoding='utf-8')
 if '# Current checkpoint: V38 provisional' not in s:f.write_text(head+s,encoding='utf-8')
f=base/'evidence_report_20261007.md';s=f.read_text(encoding='utf-8')
if '| V37 offline integration |' not in s:
 s=s.replace('| Strong gust/delayed control |','| V37 offline integration | Five navigation passes; complete offline suite 8 failed, 1687 passed, 8 skipped; UI state and seven inside-margin stationary-hold fixtures | Complete failed suite preserved; V38 source and fixture corrections remain unaccepted |\n| Strong gust/delayed control |',1)
 f.write_text(s,encoding='utf-8')
f=base/'evidence_index_20261007.json';index=json.loads(f.read_text(encoding='utf-8'))
index['current_continuation']=dict(source='V38 provisional',source_files=len(new),archive_sha256=p['archive_sha256'],headless_rtf=1.,remaining='Five exact-source targeted flights, complete reduced-scope offline suite, five rendered acceptances, 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v38_targeted_20261008'];index['active_trial']=index['active_runs'][0]
index['accepted_source']=None;index['qualification_complete']=False
index['verification']['v38_focused']=dict(log='logs/reliability_v38_integrated_focused_20261009.log',checks=152,accepted=False)
f.write_text(json.dumps(index,indent=2),encoding='utf-8')
print('V38 final-source qualification active; full V37 failure retained')
