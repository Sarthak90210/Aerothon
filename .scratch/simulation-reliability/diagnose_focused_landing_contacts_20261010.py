"""Establish the cause of every unexpected contact in the failed focused return.

Reads the preserved V39 focused run without writing to it, classifies all
6,805 records against independent truth and onboard telemetry, and replays the
corrected grader over a copy carrying the landing contract the corrected
driver would have written at its own LAND command. This is a diagnosis, not a
qualification result: no grade, summary or closure is produced.

    python3 .scratch/simulation-reliability/diagnose_focused_landing_contacts_20261010.py \
        logs/reliability_reduced_v39_focused_split_s20261003_20261009 OUT.json
"""
import bisect
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'sim'))
from native_contact_evidence import qualify_vehicle_contacts    # noqa: E402

CHANNELS = ('evaluation_vehicle_contacts.jsonl', 'vehicle_contact_ready.json',
            'flight_vehicle.sdf', 'evaluation_target.json')


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def nearest(poses, times, stamp):
    i = bisect.bisect_left(times, stamp)
    choices = [j for j in (i-1, i) if 0 <= j < len(poses)]
    return min(choices, key=lambda j: abs(times[j]-stamp)) if choices else None


def classify(out):
    """Every unexpected pair with the evidence that explains it."""
    grade = json.loads((out/'grade.json').read_text())
    unexpected = grade['aircraft_contact_evidence']['unexpected_contacts']
    poses = sorted(rows(out/'evaluation_vehicle_truth.jsonl'), key=lambda r: r['stamp'])
    times = [r['stamp'] for r in poses]
    onboard = sorted(rows(out/'onboard.jsonl'), key=lambda r: r['stamp'])
    stamps = [r['stamp'] for r in onboard]
    armed = [r['stamp'] for r in onboard
             if r.get('flight', {}).get('data', {}).get('armed') is True]
    first = min(armed)
    groups = {}
    for record in unexpected:
        stamp = record['stamp']
        pose = poses[nearest(poses, times, stamp)]
        j = bisect.bisect_right(stamps, stamp)-1
        flight = (onboard[j] if j >= 0 else {}).get('flight', {}).get('data', {})
        key = (record['vehicle'], record['other'],
               'before first arm' if stamp < first else flight.get('mode'))
        group = groups.setdefault(key, dict(
            vehicle=record['vehicle'], other=record['other'],
            fcu_mode=flight.get('mode'), before_first_arm=stamp < first,
            records=0, first_stamp=stamp, last_stamp=stamp,
            truth_height_m=[pose['z'], pose['z']], truth_xy=[pose['x'], pose['y']],
            max_depth_m=0.))
        group['records'] += 1
        group['first_stamp'] = min(group['first_stamp'], stamp)
        group['last_stamp'] = max(group['last_stamp'], stamp)
        group['truth_height_m'] = [min(group['truth_height_m'][0], pose['z']),
                                   max(group['truth_height_m'][1], pose['z'])]
        group['max_depth_m'] = max(group['max_depth_m'], max(record['depth']))
    return first, sorted(groups.values(), key=lambda g: -g['records'])


def reconstructed_contract(out):
    """The contract the corrected driver writes at its own LAND command.

    corridor_trial.LandingContract records the onboard FCU local position at
    the tick that commands the landing. The preserved driver trace holds that
    same tick's pose, so the replay uses it rather than any later position.
    """
    driver = rows(out/'trial_driver.jsonl')
    land = next(r for r in driver if r['phase'] == 'LAND')
    return dict(commanded_stamp=land['stamp'], frame='home_local_enu',
                anchor=[land['pose'][0], land['pose'][1]], radius_m=1.5,
                pose_capture_stamp=None, max_age_s=.7,
                source='reconstructed from the preserved driver trace for diagnosis')


def replay(out, contract):
    """Grade a copy of the preserved channels; the original is never written."""
    onboard = rows(out/'onboard.jsonl')
    truth = rows(out/'evaluation_vehicle_truth.jsonl')
    layout = json.loads((out/'layout.json').read_text())
    with tempfile.TemporaryDirectory() as workspace:
        work = Path(workspace)
        for name in CHANNELS:
            shutil.copyfile(out/name, work/name)
        before = qualify_vehicle_contacts(work, onboard, truth, layout)
        (work/'landing_contract.json').write_text(json.dumps(contract, indent=2))
        after = qualify_vehicle_contacts(work, onboard, truth, layout)
    return before, after


def summarise(result):
    keep = ('valid', 'contact_free', 'failures', 'ground_canary', 'channels',
            'heartbeat_count', 'allowed_ground_or_grip_pairs',
            'declared_landing_pairs', 'first_armed_stamp', 'last_armed_stamp')
    out = {k: result[k] for k in keep if k in result}
    out['unexpected_contact_records'] = len(result['unexpected_contacts'])
    out['unexpected_pairs'] = sorted({(r['vehicle'], r['other'])
                                      for r in result['unexpected_contacts']})
    return out


def main():
    out = Path(sys.argv[1])
    first, groups = classify(out)
    contract = reconstructed_contract(out)
    before, after = replay(out, contract)
    configuration = json.loads((out/'configuration.json').read_text())
    report = dict(
        run=str(out), preserved=True, first_armed_stamp=first,
        payload_fixture=configuration['payload_fixture'],
        world_payload_pose=world_payload_pose(out),
        spawn_pose=spawn_pose(out),
        detachable_joint_in_flown_vehicle='DetachableJoint' in (out/'flight_vehicle.sdf').read_text(),
        unexpected_groups=groups,
        reconstructed_landing_contract=contract,
        replay_without_contract=summarise(before),
        replay_with_contract=summarise(after),
        conclusion=dict(
            payload_records=sum(g['records'] for g in groups
                                if 'aerothon_payload' in g['other']),
            payload_cause='the unloaded fixture removes the detachable joint but the '
                          'world still spawns the cargo under the airframe centre, so it '
                          'drops onto the pad against a landing skid before the flight arms',
            ground_records=sum(g['records'] for g in groups
                               if 'ground' in g['other']),
            ground_cause='the trial lands where the return lane ends, which the contact '
                         'rule could only accept within 1 m of home',
            hazardous_airborne_contacts=[g for g in groups
                                         if g['truth_height_m'][0] > .45]))
    Path(sys.argv[2]).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items()
                      if k != 'unexpected_groups'}, indent=2))


def world_payload_pose(out):
    world = (out/'flight_world.sdf').read_text()
    i = world.index('<model name="aerothon_payload">')
    a = world.index('<pose>', i)
    return [float(v) for v in world[a+6:world.index('</pose>', a)].split()[:3]]


def spawn_pose(out):
    world = (out/'flight_world.sdf').read_text()
    i = world.index('<name>aerothon_iris</name>')
    a = world.index('<pose>', i)
    return [float(v) for v in world[a+6:world.index('</pose>', a)].split()[:3]]


if __name__ == '__main__':
    main()
