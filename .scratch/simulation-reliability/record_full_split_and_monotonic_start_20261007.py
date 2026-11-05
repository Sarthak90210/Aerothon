"""Record closed rendered evidence and the next explicitly unqualified tests."""
import json
from pathlib import Path
root = Path(__file__).resolve().parents[2]
base = Path(__file__).parent
run = 'logs/reliability_render_split_guard_full_s20261003_20261007'
summary = json.loads((root / run / 'summary.json').read_text())
grade = json.loads((root / run / 'grade.json').read_text())
index_path = base / 'evidence_index_20261007.json'
index = json.loads(index_path.read_text(encoding='utf-8'))
index['runs']['isolated guard full rendered split'] = dict(path=run, scope='Full rendered normal startup', result=summary,
    measured_corridor_clearance_m=grade['measured_corridor_clearance_m'],
    closure=run+'/closed_full_review_20261007.json', accepted_source=False)
index['active_runs'] = ['logs/reliability_monotonic_search_escape_field_s2_navigation_20261007',
                       'logs/reliability_monotonic_search_escape_full_offline_20261007.log']
index['next_diagnostic'] = index['active_runs'][0]
index['accepted_source'] = None
index_path.write_text(json.dumps(index, indent=2)+'\n', encoding='utf-8')
update = '''

07 October continuation: the isolated guard's full rendered split mission
closed GRADE_PASS, all 22 required checks passed. Native minimum corridor
clearance is 0.7380697531 m, restricted-zone clearance 3.2156264652 m,
flight time 455.0 simulated seconds, payload error 0.10 m and home landing
offset 0.31 m. Recorded FCU disarm, calibrated motor delivery, camera timeline,
runtime/source/archive hashes and owned module imports are verified in
logs/reliability_render_split_guard_full_s20261003_20261007/closed_full_review_20261007.json.
Search QR/red captures each measured 20.0 Hz in simulated time, about 5.16 Hz
on the host; p95 simulated processing latency is 0.233/0.231 s respectively.
This closes the previously active split run. The guard remains isolated:
coupled gust cases fail and other required courses/final source are pending.

The field-2 timing audit now separates return BANNER_ALIGN (142.38 s) from
outbound alignment, and records SEARCH_QR 595.53 s, 250.13 m of captured FCU
travel. Repeated braking/replanning is present even with unchanged exclusion
counts. A minimal regression proves 2 cm cross-track motion invalidates the
exact nearest-edge escape endpoint. The root router now allows continuation
through that same nearest exit edge only if distance to every observed paint
rectangle is nondecreasing; existing paint and other-obstacle checks remain.
The reproduction first fails (1 failed, 12 passed); related tests then pass
127/127 including rejection of a diagonal that initially approaches paint.
This correction is provisional. Frozen 900-file source archive SHA256 is
23eb0534d929bf23920bc7aafe96647ca1fee2a01c116458dd16211d3c55a5d9.
A field-seed-2 object-level trial and a full offline rerun are active under
logs/reliability_monotonic_search_escape_*_20261007. No new flight result is
claimed. The prior 1440/3 suite belongs to the earlier source. The 200-case
campaign and accepted-source designation remain pending.
'''
for name in ('status.md', 'evidence_report_20261007.md'):
    path = base / name
    text = path.read_text(encoding='utf-8')
    if name == 'status.md':
        text = text.replace('# Current progress\n', '# Current progress\n'+update+'\nHistorical checkpoints below are retained; the continuation above supersedes active-run claims.\n', 1)
    else:
        text += update
    path.write_text(text, encoding='utf-8')
print('Closed split evidence and active tests recorded; accepted source remains unset')
