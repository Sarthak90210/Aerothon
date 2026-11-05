"""Record a provisional source and keep qualification gates explicit."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v21_source_20261008'
prov=json.loads((source/'provenance.json').read_text())
old=json.loads((root/'.scratch/reduced_scope_v20_candidate_20261008/source_manifest.json').read_text())
new=json.loads((root/'.scratch/reduced_scope_v21_candidate_20261008/source_manifest.json').read_text())
changes=dict(added=[n for n in new if n not in old],changed=[n for n in new if n in old and new[n]!=old[n]],
    removed=[n for n in old if n not in new],accepted_source=False,
    thresholds_unchanged=True,lidar_filter_unchanged=True,normal_actuators_unchanged=True)
(source/'change_from_v20.json').write_text(json.dumps(changes,indent=2))
headline=f'''# Current checkpoint: V21 provisional

No accepted source. V21 freezes {len(new)} controlled files, archive SHA256
{prov['archive_sha256']}.
All 11 normal-startup imports match this freeze. A real search-leaf regression
failed before the fix: three distinct fresh whole-region captures still waited
through repeated full sweeps. V21 starts the existing guarded orbit from a
stable non-outbound whole green lead. It requires distinct capture-associated
poses, freshness, settled camera and consistent measured lead positions.
Green alone never supplies identity or gate-crossing permission. Existing
orbit bounds, fence/red/lidar guards, normal timing and all acceptance thresholds
remain unchanged. 124 focused search/capture/framing/handover/landing checks pass.

Five two-worker same-source navigation cases are active, with retained mild
random seed 3 and field seed 2 first. Final offline, five full native rendered
acceptances and 96 eligible campaign flights remain gated. Scope stays 120
selected, 24 negative geometry classifications and 80 weather exclusions.
No original 200-case qualification is claimed. Strong gusts and artificial
control delay remain unresolved and excluded. Earlier failures are preserved.

'''
for name in ['status.md','evidence_report_20261007.md']:
    p=base/name;s=p.read_text(encoding='utf-8')
    if '# Current checkpoint: V21 provisional' not in s:p.write_text(headline+s,encoding='utf-8')
p=base/'evidence_index_20261007.json';index=json.loads(p.read_text())
index['current_continuation']=dict(source='V21 provisional',source_files=len(new),archive_sha256=prov['archive_sha256'],remaining='Five targeted trials, final offline suite, five native rendered acceptances and 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v21_targeted_20261008'];index['active_trial']='logs/reliability_reduced_v21_targeted_20261008'
index['reduced_scope']['classification_audit']='logs/reliability_reduced_scope_v21_source_20261008/planned_geometry_scope.json'
index.setdefault('verification',{})['v21_startup_and_focused']=dict(startup='logs/reliability_reduced_scope_v21_source_20261008/installed_startup_imports.json',
    red='logs/reliability_v21_green_lead_red_20261008.log',focused='logs/reliability_v21_green_lead_focused_20261008.log',checks=124,accepted=False)
p.write_text(json.dumps(index,indent=2),encoding='utf-8')
for name in ['08-rendered-return-clearance.md','37-search-overlapping-exclusion-escape.md']:
    with (base/'issues'/name).open('a',encoding='utf-8') as f:
        f.write('\n08 October V21 continuation: V20 fields 1/2/3 and mild random 4 passed navigation; mild random 3 still exceeded 900 seconds. All actually disarmed with zero contacts/fence breaches. V21 recovers the observed return-search delay by starting the existing bounded guarded orbit after three stable fresh whole-region captures. Actual-leaf red and 124 focused green checks are archived, and all 11 normal-startup imports match the freeze. Five same-source trials are active. No final offline/native/campaign acceptance yet.\n')
print(json.dumps(changes,indent=2))
