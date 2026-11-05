"""Independent file-only review; never imports ROS, simulator or drone code."""
import argparse
import hashlib
import json
import math
import statistics
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text())


def stable(t, now):
    keys = ('stamp', 'alt', 'vz', 'speed', 'tilt_deg', 'accel_residual', 'effort')
    return bool(t and all(isinstance(t.get(k), (int, float)) and math.isfinite(t[k])
                          for k in keys) and 0 <= now-t['stamp'] <= .5
                and t['alt'] > 0 and 0 < t['effort'] < 1
                and abs(t['vz']) <= .15 and t['speed'] <= .25
                and t['tilt_deg'] <= 8 and abs(t['accel_residual']) <= .6)


def review(out):
    report = dict(run=str(out.relative_to(ROOT)), scope='independent file review only')
    summary = load(out/'summary.json')
    grade = load(out/'grade.json')
    report['acceptance'] = dict(passed=summary['acceptance_pass'],
        checks_passed=sum(bool(v) for v in grade['checks'].values()),
        checks_total=len(grade['checks']), failures=summary['failures'],
        flight_time_s=summary['flight_time_s'], final_armed=summary['final_armed'],
        corridor_clearance_m=grade['measured_corridor_clearance_m'],
        restricted_zone_clearance_m=grade['measured_red_clearance_m'])
    zip_path = out/'recorded_source.zip'
    with zipfile.ZipFile(zip_path) as z:
        manifest = json.loads(z.read('archive_manifest.json'))
        bad = [name for name, sha in manifest.items()
               if digest(z.read('source/'+name)) != sha]
        recorded = {}
        for name in ('source_manifest.json', 'qualification_tools_manifest.json'):
            for path, sha in load(out/name).items():
                key = path.split('/AEROTHON/', 1)[-1] if path.startswith('/mnt/') else path
                recorded[key] = sha
        disagreement = sorted(set(recorded) ^ set(manifest))
        disagreement += [k for k in recorded.keys() & manifest.keys()
                         if recorded[k] != manifest[k]]
    runtime = load(out/'runtime_configuration_manifest.json')
    bad_assets = [name for name, sha in runtime['sha256'].items()
                  if digest((out/name).read_bytes()) != sha]
    report['provenance'] = dict(archive_sha256=digest(zip_path.read_bytes()),
        source_files=len(manifest), archived_source_hash_mismatches=bad,
        archived_vs_recorded_manifest_mismatches=disagreement,
        runtime_assets=len(runtime['sha256']), runtime_asset_hash_mismatches=bad_assets,
        runtime_parameter_files=len(runtime['parameter_sources']))
    profile = load(out/'frozen_calibration.json')
    ceiling = (profile['loaded_mean']-3*profile['loaded_std']+
               profile['unloaded_mean']+3*profile['unloaded_std'])/2
    report['calibration'] = dict(profile_sha256=digest((out/'frozen_calibration.json').read_bytes()),
        source=profile['source'], unloaded_ceiling=ceiling, fixtures=[])
    for kind in ('loaded', 'unloaded'):
        path = ROOT/profile[kind+'_recording']
        samples = load(path)
        computed = dict(mean=statistics.mean(samples), std=statistics.stdev(samples))
        report['calibration']['fixtures'].append(dict(mode=kind, path=str(path.relative_to(ROOT)),
            samples=len(samples), samples_sha256=digest(path.read_bytes()),
            mean=computed['mean'], std=computed['std'],
            frozen_statistics_match=abs(computed['mean']-profile[kind+'_mean']) < 1e-12
                and abs(computed['std']-profile[kind+'_std']) < 1e-12,
            sampling_config=load(path.parent/'sampling_config.json'),
            exact_source_manifest_present=(path.parent/'source_manifest.json').exists(),
            runtime_manifest_present=(path.parent/'runtime_configuration_manifest.json').exists()))
    first_done = last = None
    first_disarmed_after_result = None
    for line in (out/'onboard.jsonl').open():
        row = json.loads(line)
        last = row
        o = row.get('observation') or {}
        if first_done is None and row.get('mission') == 'WINCH_DROP' and o.get('state') == 'DONE':
            first_done = row
        if first_disarmed_after_result is None and row.get('result') and row.get('flight', {}).get('data', {}).get('armed') is False:
            first_disarmed_after_result = row['stamp']
    if first_done:
        o = first_done['observation']
        motor = first_done['motor_outputs']['data']
        h = motor['header']['stamp']; captured = h['sec']+h['nanosec']*1e-9
        p = profile['motor_config']; values = [motor['channels'][i] for i in p['motor_channels']]
        effort = statistics.mean(((v-p['pwm_min'])/(p['pwm_max']-p['pwm_min']))**2 for v in values)
        report['delivery'] = dict(decision_stamp=o['stamp'], recorded_stamp=first_done['stamp'],
            attempt=o['attempt'], priority=o['decision_priority'],
            touchdown_inferred=o['touchdown_inferred'], detachment_inferred=o['detachment_inferred'],
            confirmed=o['delivery_confirmed'], visual_ground_support_inferred=o['visual_ground_support_inferred'],
            visual_frames=o['visual_frames'], provisional_probe_used=o['provisional_probe_used'],
            estimated_payout_m=first_done['winch']['payout_estimate_m'],
            payout_basis=first_done['winch']['payout_basis'],
            telemetry_stable_independently_recomputed=stable(o['decision_telemetry'], o['stamp']),
            decision_effort=o['decision_telemetry']['effort'], recomputed_raw_motor_effort=effort,
            raw_motor_channels=values, raw_motor_capture_stamp=captured,
            raw_motor_age_s=first_done['stamp']-captured, raw_motor_unloaded=effort < ceiling,
            aircraft_armed=first_done['flight']['data']['armed'])
    audits = {name: load(out/name) for name in ('decision_inputs.json', 'decision_inputs_navigation.json')}
    report['input_isolation'] = {name: dict(passed=a['pass'], nodes=list(a['nodes']),
        forbidden_subscriptions=a['forbidden_subscriptions'], missing_nodes=a['missing_nodes'],
        scope=a['scope']) for name, a in audits.items()}
    timeline = load(out/'video_timeline.json')
    report['recording'] = dict(**timeline, disarmed_result_first_recorded_stamp=first_disarmed_after_result,
        last_onboard_stamp=last['stamp'], last_onboard_armed=last['flight']['data']['armed'],
        camera_capture_reaches_disarmed_result=first_disarmed_after_result is not None
            and timeline['last_capture_stamp'] >= first_disarmed_after_result,
        review_redecoded_video=False)
    report['detector_rates'] = grade['detector_rates']['search']
    return report


def review_cut(out):
    report = dict(run=str(out.relative_to(ROOT)), scope='recording cut boundary; no full acceptance claim')
    rows = [json.loads(line) for line in (out/'onboard.jsonl').open()]
    last = rows[-1]
    failed = next((r for r in rows if (r.get('result') or {}).get('state') == 'FAILED'), None)
    report['result'] = load(out/'recorded_result.json')
    report['last_onboard'] = dict(stamp=last['stamp'], mission=last.get('mission'),
        flight=last['flight'], pose=last['pose'], velocity=last['velocity'],
        motor_outputs=last['motor_outputs'])
    after = [r for r in rows if failed and r['stamp'] >= failed['stamp']]
    report['after_failure'] = dict(first_failed_result_recorded_stamp=(failed or {}).get('stamp'),
        onboard_samples=len(after), disarmed_state_seen=any(
            r.get('flight', {}).get('data', {}).get('armed') is False for r in after))
    report['last_records'] = {}
    for name in ('camera_frames.jsonl', 'camera_capture_events.jsonl', 'evaluation_truth.jsonl',
                 'evaluation_vehicle_truth.jsonl', 'evaluation_contacts.jsonl',
                 'flight_commands.jsonl', 'winch_commands.jsonl', 'onboard_lidar.jsonl'):
        path = out/name
        latest = None
        with path.open('rb') as f:
            # Seek only the final few records instead of rereading large lidar journals.
            f.seek(max(0, path.stat().st_size-65536))
            lines = f.read().splitlines()
            latest = json.loads(lines[-1])
        if name in ('evaluation_contacts.jsonl', 'onboard_lidar.jsonl'):
            latest = {k:v for k,v in latest.items() if k not in ('contacts', 'ranges', 'intensities')}
        report['last_records'][name] = latest
    report['runner_exit_code'] = (out/'runner_exit_code.txt').read_text().strip()
    archive = out/'recorded_source.zip'
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read('archive_manifest.json'))
        bad = [p for p, sha in manifest.items() if digest(z.read('source/'+p)) != sha]
    runtime = load(out/'runtime_configuration_manifest.json')
    bad_assets = [p for p, sha in runtime['sha256'].items()
                  if digest((out/p).read_bytes()) != sha]
    report['provenance'] = dict(archive_sha256=digest(archive.read_bytes()),
        source_files=len(manifest), archived_source_hash_mismatches=bad,
        runtime_assets=len(runtime['sha256']), runtime_asset_hash_mismatches=bad_assets)
    report['complete_recording_through_disarm'] = False
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--cut-only', action='store_true')
    args = parser.parse_args()
    result = (review_cut if args.cut_only else review)(args.run.resolve())
    with args.out.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps(dict(report=str(args.out), acceptance=result.get('acceptance'),
                          provenance=result['provenance'], delivery=result.get('delivery'),
                          after_failure=result.get('after_failure'))))
