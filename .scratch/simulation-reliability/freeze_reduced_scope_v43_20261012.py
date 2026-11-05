"""Freeze the clarified-arena (Phase 2) source as V43.

V43 flies the arena the organisers clarified, with every dimension entered at
the GCS and applied before START (the operator's path), and the algorithm
changes flying it exposed. Flown decision modules change, so no earlier flight
evidence describes this source. The freeze records exactly what changed. It
never claims acceptance.
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

PREVIOUS = root/'.scratch/reduced_scope_v42_candidate_20261011'
PREVIOUS_SOURCE = root/'logs/reliability_reduced_scope_v42_source_20261011'
# V42 recorded no import list; the decision modules are V41's list.
DECISION_MODULES = root/'logs/reliability_reduced_scope_v41_source_20261010/installed_startup_imports.json'
SCOPE = ('Reduced qualification: normal actuator response, no artificial transport '
         'queue; strong wind/gust above moderate field envelope excluded')

out = root/'.scratch/reduced_scope_v43_candidate_20261012'
out.mkdir(exist_ok=False)
evidence = root/'logs/reliability_reduced_scope_v43_source_20261012'
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
# Phase 2 changes the mission tree; if it did not move, this is not the source
# it claims.
assert {'mission_bt.mission_tree'} <= set(changed_decisions), sorted(changed_decisions)

review = dict(
    scope=SCOPE, version='V43', files=len(manifest),
    archive_sha256=hashlib.sha256((evidence/'frozen_source.zip').read_bytes()).hexdigest(),
    accepted_source=False, original_200_case_qualified=False,
    previous_version='V42',
    previous_archive_sha256=json.loads(
        (PREVIOUS_SOURCE/'provenance.json').read_text())['archive_sha256'],
    changed_files={name: dict(previous=previous.get(name), current=manifest.get(name))
                   for name in changed},
    change_summary=[
        'operator path: scripts/gcs_operator.py saves and applies a dimension '
        'preset over the aggregator before START; fly_headless --gcs-preset and '
        'AEROTHON_GCS_PRESET run every simulated flight that way',
        'worlds from the same dimensions (world_from_dimensions.py): side-by-side '
        'corridors, rod-hung/laid/both banners as wide as the corridor, orange '
        'banners at the openings not to use, half-width obstacles, one 5 ft red '
        'zone, 1 m QRs; banner height unknown, flown at 0.30 m and 1.15 m',
        'perception_banner: green-only search once colours are supplied; aspect '
        'limits from the GCS banner size (banner_shape.py)',
        'mission_tree: square-up descent capped below the banner height and aimed '
        'by the GCS lower edge; laid square-up closes in to the stand-off band '
        'and measures past the mouth widest-first (edge-on wall = corridor axis), '
        'keeping the sheet range through identification flicker; duck-under looks '
        'up for an unseen hung banner; crossing cap allows for the stand-off; '
        'return stand-off 7.5 m for ground gates; zone side judged past the corridors '
        'end; ground-pass back-off and backward relocation; orbit legs and '
        'square-up steps refuse a wall alongside; descents past the wall tops only '
        'where the aircraft has been low; landing commits when the start QR leaves '
        'the frame just above the floor; a laid sheet identified from above is '
        'carried by where it lies at gate height (green at that spot is the sheet); '
        'on a ground-only arena the return search looks down (GROUND) from look '
        'height and ranges a sighting where it meets the ground; gate height kept '
        'under the hazard band of a hung banner',
        'perception_banner identity along the panel outline (border-outline): a '
        'slanted laid sheet is identified, one shadowed edge allowed with three framed',
        'GCS lidar calibration mode: capture ahead/port, solve the mount, apply live '
        'and keep it on the aircraft (scan_mount, lidar_calibration)',
        'arena_dimensions: start QR, hung-banner lower edge and wall height steer '
        'the mission; clarified preset hangs the banner from the wall top'],
    flown_decision_modules_changed=changed_decisions,
    flown_decision_modules_unchanged=unchanged_decisions,
    flight_evidence='No earlier flight evidence applies to this source: flown '
                    'decision modules changed. V42 results keep their own labels.')
(evidence/'provenance.json').write_text(json.dumps(review, indent=2)+'\n')
print(json.dumps({k: v for k, v in review.items()
                  if k not in ('flown_decision_modules_unchanged', 'changed_files')},
                 indent=2))
print(f'{len(changed)} files changed since V42')
