"""Register provisional V32 and preserve closed V31 restricted-zone failure."""
import json
from pathlib import Path
root = Path(__file__).resolve().parents[2]
base = root / '.scratch/simulation-reliability'
source = root / 'logs/reliability_reduced_scope_v32_source_20261008'
new = json.loads((root / '.scratch/reduced_scope_v32_candidate_20261008/source_manifest.json').read_text())
old = json.loads((root / '.scratch/reduced_scope_v31_candidate_20261008/source_manifest.json').read_text())
p = json.loads((source / 'provenance.json').read_text())
(source / 'change_from_v31.json').write_text(json.dumps(dict(accepted_source=False, changed=[n for n in new if n in old and new[n] != old[n]], added=[n for n in new if n not in old], thresholds_unchanged=True, lidar_filter_unchanged=True, normal_response_s=.6, extra_queue_s=0.), indent=2))
head = f'''# Current checkpoint: V32 provisional, hazard-hold verification active

V32 freezes {len(new)} controlled files, archive SHA256
{p['archive_sha256']}. All 99 focused checks pass, covering search-anchor
revalidation, unknown or stale motion, obstructed escape, distinct stopping
captures, corridor registration, gate motion and visual landing capture gaps.
Normal startup resolves all 11 decision/perception modules to this freeze.

V31 safely closed three targeted navigation trials. Field seeds 2 and 3 passed
all 13 navigation checks and actually disarmed with PRECISE landing. Mild
random seed 3 passed corridor clearance (.7372377792461882 m), return, time
and actual disarm, but FAILED restricted-zone clearance at 1.2139113263915782
m against the unchanged 1.50 m requirement. All three had zero contacts and
fence breaches; two unflown trials were cancelled. These headless trials do
not qualify rendered perception or motor delivery. Original grades, source,
configurations, recordings and disarms remain in the closed failure review.

The failed minimum occurred during QR search while the controller repeatedly
held an anchor newly covered by observed restricted-zone paint. The actual
search-braking seam failed before the fix. V32 revalidates both active and
completed stationary anchors against current observed exclusions, requires
fresh measured motion, and uses the existing router to certify the nearest
edge escape. If new paint blocks that escape, it latches a fresh stationary
position. It cannot finish escape while inside the original safety margin.
Acceptance thresholds, thin obstacles, filters, actuator response and timing
are unchanged. Whole-flight restricted-zone clearance remains unverified.

Five exact-source targeted cases rerun before one final offline suite, five
native rendered 22/22 acceptances and the 96 eligible campaign flights.
No accepted source exists. Strong gusts and artificially delayed control
remain unresolved, preserved and excluded. The reduced matrix has 120
selected entries, 80 weather exclusions and 24 negative geometry
classifications; those negative entries are not passes. No original
200-case qualification is claimed.

'''
for name in ('status.md', 'evidence_report_20261007.md'):
    f = base / name
    s = f.read_text(encoding='utf-8')
    if '# Current checkpoint: V32 provisional' not in s:
        f.write_text(head + s, encoding='utf-8')
f = base / 'evidence_report_20261007.md'
s = f.read_text(encoding='utf-8')
if '| V31 mild random 3 |' not in s:
    s = s.replace('| Strong gust/delayed control |', '| V31 mild random 3 | Restricted-zone clearance 1.2139113263915782 m FAIL; corridor .7372377792461882 m, 835 s airborne, actual disarm, zero contacts/fence breaches; field 2 and 3 navigation PASS; two unflown cancelled | FAIL preserved; V32 hazard-hold recovery remains unaccepted |\n| Strong gust/delayed control |', 1)
    f.write_text(s, encoding='utf-8')
f = base / 'evidence_index_20261007.json'
index = json.loads(f.read_text(encoding='utf-8'))
index['current_continuation'] = dict(source='V32 provisional', source_files=len(new), archive_sha256=p['archive_sha256'], remaining='Five V32 targeted trials, final offline suite, five rendered acceptances, 96 eligible campaign flights')
index['active_runs'] = ['logs/reliability_reduced_v32_targeted_20261008']
index['active_trial'] = index['active_runs'][0]
index['accepted_source'] = None
index['qualification_complete'] = False
index['verification']['v31_closed_failure_review'] = 'logs/reliability_reduced_scope_v31_source_20261008/targeted_failure_closed_review.json'
index['verification']['v32_focused'] = dict(red='logs/reliability_search_hazard_hold_red_20261008.log', focused='logs/reliability_v32_hazard_hold_focused_20261008.log', checks=99, accepted=False)
index['verification']['v31_red_diagnosis'] = 'logs/reliability_reduced_v31_targeted_20261008/my_world_random_s3/red_clearance_diagnosis.json'
f.write_text(json.dumps(index, indent=2), encoding='utf-8')
for name in ('08-rendered-return-clearance.md', '37-search-overlapping-exclusion-escape.md'):
    f = base / 'issues' / name
    s = f.read_text(encoding='utf-8')
    if 'V32 hazard-hold checkpoint' not in s:
        f.write_text(s + '\n\n## V32 hazard-hold checkpoint\n\nV31 field 2/3 passed navigation and disarmed. Mild random 3 passed corridor at .7372377792461882 m, but failed restricted-zone clearance at 1.2139113263915782 m. Original failure is retained. V32 revalidates latched search anchors against new observed paint and certifies escape through the existing router, stopping if blocked. 99 focused checks pass; whole-flight and rendered acceptance remain pending. Issue remains open.\n', encoding='utf-8')
print('V32 provisional registered; V31 restricted-zone failure preserved')
