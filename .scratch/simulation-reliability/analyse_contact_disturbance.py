"""Offline join of independent contact truth and passive FCU records."""
import json
import math
import statistics
import sys
from pathlib import Path

out = Path(sys.argv[1])
def rows(name):
    for line in (out/name).open():
        try: yield json.loads(line)
        except ValueError: continue

contacts = list(rows('evaluation_contacts.jsonl'))
ground = next(r['stamp'] for r in contacts if any(
    'delivery_zone' in c['collision2'] or 'ground' in c['collision2']
    for c in r['contacts']))
profile = json.loads((out/'frozen_calibration.json').read_text())
threshold = (profile['loaded_mean'] - 3*profile['loaded_std'] +
             profile['unloaded_mean'] + 3*profile['unloaded_std'])/2
samples = []
for r in rows('onboard.jsonl'):
    if not ground-5 <= r['stamp'] <= ground+45: continue
    try:
        channels = r['motor_outputs']['data']['channels'][:4]
        v = r['velocity']['data']['twist']['linear']
        a = r['imu']['data']['linear_acceleration']
        obs = r.get('observation', {})
        samples.append(dict(stamp=r['stamp'],
            effort=sum(((x-1000)/1000)**2 for x in channels)/4,
            alt=r['pose']['data']['pose']['position']['z'],
            vz=v['z'], speed=math.hypot(v['x'],v['y']),
            acceleration_residual=abs(math.sqrt(sum(a[k]**2 for k in ('x','y','z')))-9.80665),
            observer=obs.get('state'), payout_estimate=obs.get('payout_estimate_m'),
            camera_range_estimate=obs.get('camera_range_estimate_m')))
    except KeyError: continue
periods = []
for lo, hi in [(-5,0),(0,1),(1,5),(5,15),(15,30),(30,45)]:
    subset = [r for r in samples if ground+lo<=r['stamp']<ground+hi]
    touch = [c for r in contacts if ground+lo<=r['stamp']<ground+hi
             for c in r['contacts'] if 'claw' in c['collision2']]
    periods.append(dict(relative_interval_s=[lo,hi], samples=len(subset),
        motor_effort_mean=statistics.mean(r['effort'] for r in subset) if subset else None,
        motor_effort_min=min((r['effort'] for r in subset),default=None),
        max_acceleration_residual=max((r['acceleration_residual'] for r in subset),default=None),
        max_abs_vz=max((abs(r['vz']) for r in subset),default=None),
        claw_payload_contact_records=len(touch),
        max_claw_payload_penetration_m=max((d for c in touch for d in c['depth']),default=None)))
result = dict(contact_stamp=ground, frozen_unloading_threshold=threshold,
    periods=periods, samples=samples,
    note='Separate simulator truth joined only after capture. Contact and low PWM correlate; this does not measure contact forces or prove causation.')
(out/'contact_disturbance_analysis.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='samples'},indent=2))
