"""Freeze the unloaded payload fixture and the declared land-in-place contract.

V40 differs from V39 only in the focused trial's scene and its independent
contact contract. The freeze records which controlled files changed and
proves that every flown decision module is byte-identical to V39, so V39's
targeted navigation evidence still describes this source's flight behaviour.
It never claims acceptance.
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

PREVIOUS = root/'.scratch/reduced_scope_v39_candidate_20261008'
DECISION_MODULES = root/'logs/reliability_reduced_scope_v39_source_20261008/installed_startup_imports.json'
SCOPE = ('Reduced qualification: normal actuator response, no artificial transport '
         'queue; strong wind/gust above moderate field envelope excluded')

out = root/'.scratch/reduced_scope_v40_candidate_20261010'
out.mkdir(exist_ok=False)
evidence = root/'logs/reliability_reduced_scope_v40_source_20261010'
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
# Every module the running aircraft imports for a decision. If one of these
# changed, targeted flight evidence from V39 would have to be reflown.
decision = json.loads(DECISION_MODULES.read_text())
unchanged_decisions = {}
for module, record in decision.items():
    name = str(Path(record['file']).resolve()).replace('\\', '/')
    name = name[name.index('/src/')+1:] if '/src/' in name else name
    assert manifest[name] == record['sha256'], f'{module} changed since V39'
    unchanged_decisions[module] = dict(file=name, sha256=record['sha256'])

review = dict(
    scope=SCOPE, version='V40', files=len(manifest),
    archive_sha256=hashlib.sha256((evidence/'frozen_source.zip').read_bytes()).hexdigest(),
    accepted_source=False, original_200_case_qualified=False,
    previous_version='V39',
    previous_archive_sha256=json.loads(
        (root/'logs/reliability_reduced_scope_v39_source_20261008/provenance.json').read_text())['archive_sha256'],
    changed_files={name: dict(v39=previous.get(name), v40=manifest.get(name))
                   for name in changed},
    change_summary=[
        'scripts/world_spec.py, scripts/materialize_world.py: an unloaded fixture '
        'parks the cargo 1.2 m from the spawn instead of dropping it onto the pad '
        'against a landing skid',
        'sim/corridor_trial.py: the focused trial declares its land-in-place from '
        'the onboard FCU pose at the LAND command, before touchdown',
        'sim/native_contact_evidence.py: a declared land-in-place accepts the skids '
        'settling on the declared spot, under freshness, distance, speed, attitude '
        'and FCU-mode evidence; the home rule, every other collider, surface and '
        'threshold are unchanged',
        'tests: declared-landing positives and negatives, malformed-contract '
        'fail-closed, parked-payload placement, driver contract evidence'],
    flown_decision_modules_unchanged_since_v39=unchanged_decisions,
    targeted_navigation_evidence='V39 five-case navigation evidence applies to this '
                                 'source because no flown decision module changed; '
                                 'it keeps its own V39 labels')
(evidence/'provenance.json').write_text(json.dumps(review, indent=2)+'\n')
print(json.dumps({k: v for k, v in review.items()
                  if k != 'flown_decision_modules_unchanged_since_v39'}, indent=2))
