"""Freeze the planner shortcut that may no longer spend a tight origin's reserve.

V41 changes two flown decision modules, so no earlier flight evidence
describes this source: the targeted navigation cases, the focused return and
every rendered acceptance have to be reflown. The freeze records exactly
which controlled files and which flown modules changed, and the candidate
that was measured and rejected. It never claims acceptance.
"""
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root/'sim'))
from campaign_record import source_manifest                    # noqa: E402

PREVIOUS = root/'.scratch/reduced_scope_v40_candidate_20261010'
PREVIOUS_SOURCE = root/'logs/reliability_reduced_scope_v40_source_20261010'
DECISION_MODULES = PREVIOUS_SOURCE/'installed_startup_imports.json'
SCOPE = ('Reduced qualification: normal actuator response, no artificial transport '
         'queue; strong wind/gust above moderate field envelope excluded')
EXPECTED_CHANGED_DECISIONS = {'avoidance.local_planner',
                              'avoidance.fast_connected_planner_candidate'}

out = root/'.scratch/reduced_scope_v41_candidate_20261010'
out.mkdir(exist_ok=False)
evidence = root/'logs/reliability_reduced_scope_v41_source_20261010'
evidence.mkdir(exist_ok=False)

source_manifest.cache_clear()
manifest = {name.replace('\\', '/'): sha for name, sha in source_manifest(root).items()}
for name, sha in manifest.items():
    p = root/name
    target = out/name
    target.parent.mkdir(parents=True, exist_ok=True)
    assert hashlib.sha256(p.read_bytes()).hexdigest() == sha, name
    shutil.copy2(p, target)
(out/'source_manifest.json').write_text(json.dumps(manifest, indent=2))
with zipfile.ZipFile(evidence/'frozen_source.zip', 'x', zipfile.ZIP_DEFLATED) as z:
    for name in manifest:
        z.write(out/name, name)
    z.write(out/'source_manifest.json', 'source_manifest.json')

previous = json.loads((PREVIOUS/'source_manifest.json').read_text())
changed = sorted(name for name in set(previous) | set(manifest)
                 if previous.get(name) != manifest.get(name))
# Every module the running aircraft imports for a decision. Two of them are
# the planners this version changes, so every flight gate is reflown.
decision = json.loads(DECISION_MODULES.read_text())
unchanged_decisions = {}
changed_decisions = {}
for module, record in decision.items():
    name = str(Path(record['file']).resolve()).replace('\\', '/')
    name = name[name.index('/src/')+1:] if '/src/' in name else name
    if manifest[name] == record['sha256']:
        unchanged_decisions[module] = dict(file=name, sha256=record['sha256'])
    else:
        changed_decisions[module] = dict(file=name, previous=record['sha256'],
                                         current=manifest[name])
assert set(changed_decisions) == EXPECTED_CHANGED_DECISIONS, changed_decisions

review = dict(
    scope=SCOPE, version='V41', files=len(manifest),
    archive_sha256=hashlib.sha256((evidence/'frozen_source.zip').read_bytes()).hexdigest(),
    accepted_source=False, original_200_case_qualified=False,
    previous_version='V40',
    previous_archive_sha256=json.loads(
        (PREVIOUS_SOURCE/'provenance.json').read_text())['archive_sha256'],
    changed_files={name: dict(previous=previous.get(name), current=manifest.get(name))
                   for name in changed},
    change_summary=[
        'avoidance/local_planner.py, avoidance/fast_connected_planner_candidate.py: '
        'when the origin is already inside the planning reserve, the shortcut takes '
        'the longest segment that gives away no clearance before falling back to the '
        'original 0.025 m allowance that keeps such an origin reachable. The 0.70 m '
        'floor, the grid reserve, unknown-space rejection, the travel cost and the '
        'normal batch shortcut are unchanged',
        'sim/test_continuous_corridor_certificate.py and '
        'sim/fixtures/corridor_native_slalom_shortcut_split_s20261003_20261010.json: '
        'the captured tight-origin control from the failed V40 split return, which '
        'both planners fail on V40 and pass here'],
    cause='logs/reliability_reduced_v40_render_split_corridors_s20261003_20261010/'
          'clearance_diagnosis.json: the V40 split return grazed the turned board at '
          '0.6944741417890966 m in one 12-sample episode, with zero deadline overruns, '
          'while 0.836 m was available on the gap medial line',
    rejected_candidate='Applying the same no-give-away preference to the normal batch '
                       'shortcut as well: the offline split slalom traversal took 34.1 s '
                       'instead of 24.7 s and its calm clearance fell from 0.767699 m to '
                       '0.745958 m, so it was not adopted',
    preserved_red_control='logs/reliability_v40_tight_origin_shortcut_red_20261010.log',
    flown_decision_modules_changed=changed_decisions,
    flown_decision_modules_unchanged=unchanged_decisions,
    flight_evidence='No earlier flight evidence applies to this source: two flown '
                    'decision modules changed, so the targeted cases, the focused '
                    'return and every rendered acceptance are reflown. V39 and V40 '
                    'results keep their own labels and their own failures.')
(evidence/'provenance.json').write_text(json.dumps(review, indent=2)+'\n')
print(json.dumps({k: v for k, v in review.items()
                  if k != 'flown_decision_modules_unchanged'}, indent=2))
