"""Freeze the organiser-clarification source as V42.

V42 adapts the flown stack to the SAE Aerothon 2026 clarifications: banners
carry no text and are identified by colour (operator-supplied HEX) and their
3-inch white border; banners may be suspended, ground-mounted or both, and the
gate aligns to each one present in turn; the QR is matched by appearance first
and by decoded message second; the GCS supplies the banner colours and only
starts flight in GUIDED. Several flown decision modules change, so no earlier
flight evidence describes this source. The freeze records exactly what changed.
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

PREVIOUS = root/'.scratch/reduced_scope_v41_candidate_20261010'
PREVIOUS_SOURCE = root/'logs/reliability_reduced_scope_v41_source_20261010'
DECISION_MODULES = PREVIOUS_SOURCE/'installed_startup_imports.json'
SCOPE = ('Reduced qualification: normal actuator response, no artificial transport '
         'queue; strong wind/gust above moderate field envelope excluded')

out = root/'.scratch/reduced_scope_v42_candidate_20261011'
out.mkdir(exist_ok=False)
evidence = root/'logs/reliability_reduced_scope_v42_source_20261011'
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
decision = json.loads(DECISION_MODULES.read_text())
unchanged_decisions, changed_decisions = {}, {}
for module, record in decision.items():
    name = str(Path(record['file']).resolve()).replace('\\', '/')
    name = name[name.index('/src/')+1:] if '/src/' in name else name
    if manifest.get(name) == record['sha256']:
        unchanged_decisions[module] = dict(file=name, sha256=record['sha256'])
    else:
        changed_decisions[module] = dict(file=name, previous=record['sha256'],
                                         current=manifest.get(name))
# The clarification work necessarily changes the mission tree and the banner
# and QR detectors; if none of them moved, this is not the source it claims.
assert {'mission_bt.mission_tree'} <= set(changed_decisions), sorted(changed_decisions)

review = dict(
    scope=SCOPE, version='V42', files=len(manifest),
    archive_sha256=hashlib.sha256((evidence/'frozen_source.zip').read_bytes()).hexdigest(),
    accepted_source=False, original_200_case_qualified=False,
    previous_version='V41',
    previous_archive_sha256=json.loads(
        (PREVIOUS_SOURCE/'provenance.json').read_text())['archive_sha256'],
    changed_files={name: dict(previous=previous.get(name), current=manifest.get(name))
                   for name in changed},
    change_summary=[
        'perception_banner: identity by the 3-inch white border instead of '
        'lettering; colour bands from operator-supplied HEX (colours.py); '
        'detector runs in FORWARD, BANNER and the new GROUND pose',
        'perception_qr: appearance match against the start marker first '
        '(qr_appearance.py), decoded message second; match_basis reported',
        'perception_redzone: red band from the supplied colour when given',
        'camera_ctrl: GROUND named pose, -35 deg',
        'mission_tree: align_to_every_banner -- hung view first under a 60 s '
        'nothing-identified budget that flies back over the top before handing '
        'over; a 3 s GROUND glance gates the second (laid) alignment; '
        'ground-only fallback; unbudgeted hung pass as last resort. AlignToBanner '
        'ranges a laid sheet on the ground plane and requires the mouth face at '
        'that range',
        'gcs_aggregator + tauri_app: banner-colour field, test-part selector, '
        'flight starts only in GUIDED; readiness requires banner colours',
        'worlds: no decoys in flown worlds (banner_decoys.json keeps them as the '
        'negative control); banner placement suspended|ground|both; unlettered '
        'banners; headless models laid banners and the detector pose gate'],
    flown_decision_modules_changed=changed_decisions,
    flown_decision_modules_unchanged=unchanged_decisions,
    flight_evidence='No earlier flight evidence applies to this source: flown '
                    'decision modules changed, so every flight gate is reflown. '
                    'V41 results keep their own labels and their own failures.')
(evidence/'provenance.json').write_text(json.dumps(review, indent=2)+'\n')
print(json.dumps({k: v for k, v in review.items()
                  if k not in ('flown_decision_modules_unchanged', 'changed_files')},
                 indent=2))
print(f'{len(changed)} files changed since V41')
