"""Qualify live native vehicle contacts independently of geometric proxies."""
import bisect
import json
import math
from pathlib import Path
from record_vehicle_contacts import sensor_channels


def qualify_vehicle_contacts(out,onboard,vehicle_truth,layout):
    result=dict(valid=False,contact_free=False,failures=[],unexpected_contacts=[],ground_canary=False)
    try:
        out=Path(out);channels=sensor_channels(out/'flight_vehicle.sdf')
        expected={c['topic'] for c in channels};inventory={c['link']:c for c in channels}
        ready=json.loads((out/'vehicle_contact_ready.json').read_text())
        if ready['channels']!=channels or ready['all_topics_advertised'] is not True:
            raise ValueError('Readiness channel inventory does not match flown vehicle')
        rows=[json.loads(line) for line in (out/'evaluation_vehicle_contacts.jsonl').read_text().splitlines()]
        armed=[r['stamp'] for r in onboard if r.get('flight',{}).get('data',{}).get('armed') is True]
        if not armed:raise ValueError('No actual armed flight interval')
        first,last=min(armed),max(armed)
        heartbeats=[r for r in rows if r['kind']=='heartbeat']
        stamps=[r['stamp'] for r in heartbeats]
        if (len(stamps)<2 or any(not math.isfinite(t) or t<0 for t in stamps)
                or any(b<=a or b-a>1.5 for a,b in zip(stamps,stamps[1:]))
                or stamps[0]>first or stamps[-1]<last):
            raise ValueError('Native clock heartbeats do not cover flight continuously')
        if any(r['channels']!=channels or set(r['advertised_topics'])!=expected for r in heartbeats):
            raise ValueError('Missing native vehicle contact publisher')
        poses=sorted(vehicle_truth,key=lambda r:r['stamp']);times=[r['stamp'] for r in poses]
        telemetry=sorted(onboard,key=lambda r:r['stamp']);telemetry_times=[r['stamp'] for r in telemetry]
        target=json.loads((out/'evaluation_target.json').read_text())['target'] if (out/'evaluation_target.json').exists() else None
        pad=layout.get('pads',{}).get(target)
        deployment_pairs=0
        home=layout.get('home_world',[0,0]);allowed=0
        for row in rows:
            if row['kind']=='heartbeat':continue
            if row['kind']!='contacts':raise ValueError('Unknown evidence record')
            stamp=row['stamp'];channel=inventory[row['link']]
            if not math.isfinite(stamp) or stamp<0 or row['topic']!=channel['topic']:
                raise ValueError('Invalid native contact channel or stamp')
            if not isinstance(row['contacts'],list):raise ValueError('Malformed contact list')
            own={f'aerothon_iris::{row["link"]}::{name}' for name in channel['collisions']}
            for pair in row['contacts']:
                a,b=pair['collision1'],pair['collision2']
                if (not isinstance(a,str) or not isinstance(b,str) or not a or not b
                        or not isinstance(pair['depth'],list)
                        or any(not math.isfinite(d) for d in pair['depth'])):
                    raise ValueError('Malformed native contact pair')
                if a in own:vehicle,other=a,b
                elif b in own:vehicle,other=b,a
                else:raise ValueError('Contact does not belong to recorded vehicle collider')
                i=bisect.bisect_left(times,stamp)
                choices=[j for j in (i-1,i) if 0<=j<len(poses)]
                pose=poses[min(choices,key=lambda j:abs(times[j]-stamp))] if choices else None
                grounded=bool(pose and abs(pose['stamp']-stamp)<=.3
                    and pose['z']<=.45 and math.hypot(pose['x']-home[0],pose['y']-home[1])<=1.)
                normal_ground=(grounded and vehicle in {'aerothon_iris::base_link::skid_0','aerothon_iris::base_link::skid_1'}
                    and other in {'takeoff_landing_zone::pad::collision','site_ground::ground::collision'})
                expected_grip=(row['link'] in ('claw_jaw_a','claw_jaw_b')
                    and other.startswith('aerothon_payload::'))
                positions=pair.get('positions',[])
                if not isinstance(positions,list) or any(not all(math.isfinite(p[k]) for k in ('x','y','z')) for p in positions):
                    raise ValueError('Malformed native contact positions')
                j=bisect.bisect_right(telemetry_times,stamp)-1
                state=telemetry[j] if j>=0 else {}
                winch=state.get('winch_capture',{})
                winch_data=winch.get('data',{})
                receipt=winch.get('received_stamp',float('-inf'))
                # The deployed winch is meant to put its hook and cargo on
                # the target surface while the airframe remains airborne.
                # Retain these contacts as evidence; never exempt aircraft
                # colliders, walls, stale/stowed winches or other locations.
                deployment_surface=bool(row['link'] in ('claw_jaw_a','claw_jaw_b')
                    and other in ('delivery_zone_40x30::field::collision','site_ground::ground::collision')
                    and state.get('mission')=='WINCH_DROP' and pose and pose['z']>=2.
                    and abs(pose['stamp']-stamp)<=.3
                    and 0<=stamp-state.get('stamp',float('-inf'))<=.3
                    and math.isfinite(receipt) and 0<=stamp-receipt<=.3
                    and winch_data.get('state') in ('LOWERING','IDLE','STOWING','RELEASING')
                    and not winch_data.get('fault') and winch_data.get('payout_estimate_m',0)>=1.
                    and pad and positions and all(abs(p['z'])<=.2 and math.hypot(p['x']-pad[0],p['y']-pad[1])<=1. for p in positions))
                if deployment_surface:deployment_pairs+=1
                if normal_ground or expected_grip or deployment_surface:
                    allowed+=1
                    if normal_ground and stamp<first:result['ground_canary']=True
                else:result['unexpected_contacts'].append(dict(stamp=stamp,vehicle=vehicle,other=other,depth=pair['depth']))
        if not result['ground_canary']:raise ValueError('Missing preflight native skid contact canary')
        result.update(valid=True,contact_free=not result['unexpected_contacts'],channels=len(channels),
                      heartbeat_count=len(heartbeats),allowed_ground_or_grip_pairs=allowed,
                      intended_deployed_hook_target_surface_pairs=deployment_pairs,
                      first_armed_stamp=first,last_armed_stamp=last)
    except (OSError,ValueError,KeyError,TypeError,IndexError) as e:
        result['failures'].append(str(e))
    return result
