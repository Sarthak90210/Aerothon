"""Record both failed flights and successful offline checks without qualification."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=Path(__file__).parent
run='logs/reliability_monotonic_search_escape_field_s2_navigation_20261007'
review=json.loads((root/run/'closed_trial_review_20261007.json').read_text())
projection=root/run/'my_world_field_s2/return_camera_handoff_runtime_hfov_projection_20261007.json'
replay=json.loads(projection.read_text())
assert all(not any(h['admissible_geometry'] for h in r['coarse_headings']) for r in replay['records'])
assert all(any(h['admissible_geometry'] for h in r['fine_headings']) for r in replay['records'])
closure=dict(scope='Recorded-pose geometric preconditions only; actual lettering and lidar still required',
    runtime_hfov_verified=.851919,coarse_headings_admissible=False,fine_headings_admissible=True,
    replay_sha256=hashlib.sha256(projection.read_bytes()).hexdigest(),
    replay_source_sha256=hashlib.sha256((base/'replay_return_camera_handoff_20261007.py').read_bytes()).hexdigest(),
    prior_60_degree_projection_invalid=True,production_adopted=False)
with (root/run/'my_world_field_s2/return_camera_projection_closed_review_20261007.json').open('x') as f:json.dump(closure,f,indent=2)
path=base/'evidence_index_20261007.json';index=json.loads(path.read_text(encoding='utf-8'))
index['runs']['monotonic escape field2']=dict(path=run,scope=review['scope'],result=review)
index['verification']['monotonic_escape_full_offline']=json.loads((root/'logs/reliability_monotonic_search_escape_full_offline_closed_review_20261007.json').read_text())
index['verification']['return_framing_projection']=closure
index['runs']['derivative cap 1.6 rejected']=dict(path='logs/reliability_derivative_cap_1_6_coupled_20261007',result='Both physical cases contact; not installed')
index['active_runs']=['logs/reliability_fine_return_framing_field_s2_navigation_20261007']
index['next_diagnostic']=index['active_runs'][0]
path.write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
update='''

Latest closed tests: monotonic escape source passes 1442 tests, 3 skipped,
and all offline checks, verified against its unchanged 900-file archive.
Field seed2 finds the target at 601.70 simulated seconds (previous source
707.15) but fails return alignment and lands/disarms at 998.5 s airborne.
It has no obstacle contacts/fence breaches. Its 1.169191 m corridor minimum
does not qualify return traversal, which was not completed. Source/assets
and actual FCU disarm are verified; rendered cameras and motor delivery are
explicitly unqualified for this object-level trial.

Recorded-pose return projection corrected to the runtime 0.851919 rad HFOV:
all ten early alignment captures give zero geometrically admissible headings
on the 45-degree sweep, while the 15-degree sweep supplies admissible views.
The level camera misses the board vertically; a 20-degree look sees it.
The original 60-degree replay is retained as invalid runtime configuration,
not a qualification result. Geometry is only a detection precondition.
An isolated fine-framing candidate adds one bounded finer sweep, restoring
the look angle only above gate height, before physical relocation. It retains
the original lettering, freshness, range and lidar checks. Four component
controls pass. Its 901-file archive SHA256 is
dec801079383efa322d64caecc60da2850ead40253b8a40cb72725c27ae641df.
Field seed2 is active under logs/reliability_fine_return_framing_field_s2_navigation_20261007.
An initial launcher registration path error occurred after the valid freeze;
the existing archive was preserved and registration completed separately.

Derivative-cap-only gust diagnostic: dirty0 contacts at 6.1 s, late1 at 19.0 s;
logged preintegration minima 0.402512/0.408085 m. The exact baseline/candidate
and runner are archived in logs/reliability_derivative_cap_1_6_coupled_20261007.
Baseline class methods match current root; its startup wrapper differs.
Candidate rejected. No wider lidar filter or clearance reduction is installed.
No accepted final source or 200-case qualification exists.
'''
for name in ('status.md','evidence_report_20261007.md'):
    path=base/name;text=path.read_text(encoding='utf-8')
    text=text.replace('# Current progress\n','# Current progress\n'+update,1) if name=='status.md' else text+update
    path.write_text(text,encoding='utf-8')
for name in ('37-search-overlapping-exclusion-escape.md','38-rendered-velocity-response-model.md'):
    with (base/'issues'/name).open('a',encoding='utf-8') as f:f.write(update)
print('Closed root offline/field results, rejected gust candidate and active fine-framing trial indexed')
