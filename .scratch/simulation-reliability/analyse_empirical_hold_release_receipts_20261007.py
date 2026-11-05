"""Post-flight causal timeline for queued travel followed by position hold.

Use the saved still-air physical fixture, exact onboard pose and EKF velocity.
Recover received earth commands from its declared first-order response only
as evaluation. Published command diagnostics are rounded and labelled so.
"""
import hashlib
import json
import math
from pathlib import Path

root = Path(__file__).resolve().parents[2]
capture = root/'logs/reliability_gust_dirty_calm_empirical_viability_20261007.json'
report = json.loads(capture.read_text())
assert report['diagnostic_wind_profile']=='calm'
rows = report['rows']
episodes = []
active = None
for i,row in enumerate(rows):
    mode = row['detail'].get('diagnostic_mode')
    if mode=='TRAVEL' and active is None:
        active = i
    elif mode!='TRAVEL' and active is not None:
        start = rows[active]
        after = min(rows,key=lambda r:abs(r['stamp']-(row['stamp']+2.)))
        timeline = []
        for j in range(max(0,active-2),min(len(rows)-1,i+41)):
            r,nxt = rows[j],rows[j+1]
            velocity = r['detail']['ground_velocity_world_mps']
            following = nxt['detail']['ground_velocity_world_mps']
            span = nxt['stamp']-r['stamp']
            # Still air and the existing fixture's 0.6 s physical response
            # make this deconvolution exact. It is not a new drone signal.
            received = [a+.6/span*(b-a) for a,b in zip(velocity,following)]
            timeline.append(dict(stamp=r['stamp'],
                mode=r['detail'].get('diagnostic_mode'),pose=r['pose'],
                ground_velocity_world_mps=velocity,
                rounded_published_body_command_mps=[r['detail']['cmd_vx'],r['detail']['cmd_vy_left']],
                inferred_received_earth_command_mps=received,
                before_first_travel_receipt=r['stamp']<start['stamp']+.4-1e-8))
        episodes.append(dict(release_stamp=start['stamp'],
            hold_relatch_stamp=row['stamp'],first_travel_receipt_stamp=start['stamp']+.4,
            relatch_before_first_travel_receipt=row['stamp']<start['stamp']+.4-1e-8,
            travel_publication_duration_s=row['stamp']-start['stamp'],
            hold_target_world_m=row['detail']['diagnostic_hold_target_world_m'],
            forward_progress_at_relatch_m=start['pose'][0]-row['pose'][0],
            forward_progress_two_seconds_after_relatch_m=start['pose'][0]-after['pose'][0],
            timeline=timeline))
        active = None
result = dict(source='post-flight still-air fixture evaluation; no received-command deconvolution supplied to controller',
    capture_sha256=hashlib.sha256(capture.read_bytes()).hexdigest(),
    analysis_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    controller_sha256=report['source_sha256']['src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'],
    physical_response_s=.6,command_delay_s=.4,
    completed_travel_episodes=len(episodes),
    relatches_before_first_receipt=sum(e['relatch_before_first_travel_receipt'] for e in episodes),
    episodes=episodes)
out = root/'.scratch/simulation-reliability/empirical_hold_release_receipt_timeline_20261007.json'
assert not out.exists()
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(episodes=result['completed_travel_episodes'],
                     premature_relatches=result['relatches_before_first_receipt'],
                     short_episodes=[{k:v for k,v in e.items() if k!='timeline'} for e in episodes if e['relatch_before_first_travel_receipt']])))
