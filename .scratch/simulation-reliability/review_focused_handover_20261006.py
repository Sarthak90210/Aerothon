"""Read retained onboard entry histories and runtime files only. No node launch."""
import collections
import difflib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
RUNS = {
    'focused_pass': ROOT / 'logs/reliability_render_return_fcu_velocity_20261006',
    'full_source_entry': ROOT / 'logs/reliability_render_my_world_s20261003_gustfix_20261006',
    'full_bannerfix_failure': ROOT / 'logs/reliability_render_my_world_s20261003_bannerfix_20261006',
}


def time_header(data):
    stamp = data['header']['stamp']
    return stamp['sec'] + stamp['nanosec'] * 1e-9


def compact(row):
    pose = row['pose']['data']['pose']
    q = pose['orientation']
    data = row['velocity']['data']
    velocity = data['twist']['linear']
    return dict(stamp=row['stamp'], mission=row.get('mission'),
        pose=[pose['position'][key] for key in ('x', 'y', 'z')],
        yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']), 1-2*(q['y']**2+q['z']**2)),
        velocity=[velocity[key] for key in ('x', 'y', 'z')],
        speed_xy=math.hypot(velocity['x'], velocity['y']),
        velocity_capture=time_header(data),
        velocity_age_s=row['stamp']-time_header(data),
        avoidance=row.get('avoidance', {}), winch=row.get('winch', {}))


def entry(path):
    start = None
    if (path / 'trial_driver.jsonl').exists():
        with (path / 'trial_driver.jsonl').open() as source:
            start = next(json.loads(line)['stamp'] for line in source
                         if json.loads(line)['phase'] == 'RETURN_CORRIDOR')
    before = collections.deque(maxlen=80)
    rows = []
    with (path / 'onboard.jsonl').open() as source:
        for line in source:
            row = json.loads(line)
            if not all(key in row for key in ('pose', 'velocity')):
                continue
            if start is None and row.get('mission') == 'RETURN_CORRIDOR':
                start = row['stamp']
            if start is None or row['stamp'] < start:
                before.append(row)
                continue
            if row['stamp'] > start + 5:
                break
            rows.append(row)
    commands = []
    with (path / 'flight_commands.jsonl').open() as source:
        for line in source:
            row = json.loads(line)
            if start-3 <= row['stamp'] <= start+1:
                commands.append(row)
            elif row['stamp'] > start+1:
                break
    return dict(directory=str(path.relative_to(ROOT)), entry_stamp=start,
        entry=compact(rows[0]), pre_handover=[compact(row) for row in before
            if start-3 <= row['stamp']], first_five_seconds=[compact(row) for row in rows],
        commands_around_handover=commands)


def normalize_vehicle(path, remove_joint):
    model = ET.parse(path).getroot()
    removed = 0
    if remove_joint:
        for parent in model.iter():
            for child in list(parent):
                if child.tag == 'plugin' and child.attrib.get('name') == 'gz::sim::systems::DetachableJoint':
                    parent.remove(child)
                    removed += 1
    for element in model.iter():
        element.text = (element.text or '').strip()
        element.tail = ''
    mass = sum(float(e.text) for e in model.iter('mass'))
    return ET.tostring(model), removed, mass


focused = RUNS['focused_pass']
full = RUNS['full_bannerfix_failure']
manifests = {name: json.loads((path / 'runtime_configuration_manifest.json').read_text())
             for name, path in (('focused', focused), ('full', full))}
counts = {name: collections.Counter(sha for key, sha in manifest['sha256'].items()
          if key.startswith('runtime_parameters/')) for name, manifest in manifests.items()}
unmatched = {}
for name, other, path in (('focused', 'full', focused), ('full', 'focused', full)):
    difference = counts[name] - counts[other]
    unmatched[name] = [dict(file=key, content=(path/key).read_text())
        for key, sha in manifests[name]['sha256'].items()
        if key.startswith('runtime_parameters/') and sha in difference]
fmodel, _, fmass = normalize_vehicle(focused / 'flight_vehicle.sdf', False)
bmodel, removed, bmass = normalize_vehicle(full / 'flight_vehicle.sdf', True)
keys = ('world_spec.json', 'flight_world.sdf', 'flight_conditions.json', 'flight_conditions.parm',
        'layout.json', 'airframe.json', 'frozen_calibration.json')
report = dict(entries={name: entry(path) for name, path in RUNS.items()},
    runtime=dict(equal_assets={key: manifests['focused']['sha256'][key] == manifests['full']['sha256'][key]
        for key in keys}, parameter_counts={name: sum(value.values()) for name,value in counts.items()},
        parameter_content_hashes_unmatched=unmatched,
        vehicle_equal_after_removing_detachable_plugin=fmodel == bmodel,
        full_plugins_removed=removed, aircraft_link_mass_kg=dict(focused=fmass, full=bmass)))
print(json.dumps(report, indent=2))
