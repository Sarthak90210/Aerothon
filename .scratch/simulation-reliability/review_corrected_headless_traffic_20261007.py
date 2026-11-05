"""Read-only traffic review. Recorder receipt is not simulator callback time."""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser()
p.add_argument('--run',type=Path,default=ROOT/'logs/reliability_corrected_headless_focus_20261007/my_world_calm_s1')
p.add_argument('--out',type=Path,required=True)
args=p.parse_args()
assert not args.out.exists(), 'Preserve prior review snapshots'


def readlines(path):
    if not path.exists():return [],0
    rows=[];partial=0
    for line in path.read_text().splitlines():
        try:rows.append(json.loads(line))
        except ValueError:partial+=1
    return rows,partial


def capture(data):
    try:s=data['header']['stamp'];return s['sec']+s['nanosec']*1e-9
    except (KeyError,TypeError):return None


def stats(values):
    values=sorted(float(v) for v in values if math.isfinite(v))
    if not values:return None
    def q(f):return values[int((len(values)-1)*f)]
    return dict(samples=len(values),minimum=values[0],median=q(.5),p95=q(.95),maximum=values[-1],negative=sum(v<0 for v in values))


commands,command_partial=readlines(args.run/'flight_commands.jsonl')
rows,row_partial=readlines(args.run/'onboard.jsonl')
detectors,detector_partial=readlines(args.run/'detector_events.jsonl')
raw=[r for r in commands if r.get('topic')=='/mavros/setpoint_raw/local']
phases=[]
for row in raw:
    sent=capture(row['data'])
    if sent is None:continue
    if not phases or sent-phases[-1]['last_header_stamp']>1.:
        phases.append(dict(first_header_stamp=sent,last_header_stamp=sent,commands=0))
    phases[-1]['last_header_stamp']=sent;phases[-1]['commands']+=1
motions={}
for key in ('flight','pose','velocity'):
    values=[];seen={}
    for row in rows:
        if key not in row:continue
        observed=row[key];stamp=capture(observed.get('data',{}))
        if stamp is None:continue
        values.append(row['stamp']-stamp)
        seen[stamp]=observed
    stamps=sorted(seen)
    motions[key]=dict(distinct_capture_count=len(stamps),first_capture_stamp=stamps[0] if stamps else None,
        last_capture_stamp=stamps[-1] if stamps else None,
        record_age_s=stats(values),recorder_delivery_delta_s=stats(o['received_stamp']-stamp for stamp,o in seen.items()))

decisions=[];seen={}
for row in rows:
    detail=row.get('avoidance',{})
    if not isinstance(detail,dict) or 'ground_velocity_world_mps' not in detail:continue
    signature=json.dumps(detail,sort_keys=True)
    if signature in seen:continue
    seen[signature]=True
    entry=dict(recorded_stamp=row['stamp'],mission=row.get('mission'),detail=detail)
    decisions.append(entry)

detector_stats={}
for key in ('qr_timing','red_timing'):
    events=[r for r in detectors if r['detector']==key]
    distinct={r['detail']['capture_stamp']:r for r in events if isinstance(r.get('detail'),dict) and 'capture_stamp' in r['detail']}
    stamps=sorted(distinct)
    detector_stats[key]=dict(events=len(events),distinct_frames=len(stamps),
        delivered_distinct_hz=(len(stamps)-1)/(stamps[-1]-stamps[0]) if len(stamps)>1 else None,
        declared_processing_latency_s=stats(r['detail']['processed_stamp']-stamp for stamp,r in distinct.items()),
        recorder_delivery_latency_s=stats(r['received_stamp']-stamp for stamp,r in distinct.items()))

command_topics=collections.Counter(r['topic'] for r in commands)
last=rows[-1] if rows else None
report=dict(run=str(args.run),configuration=json.loads((args.run/'configuration.json').read_text()),
    source_manifest_sha256=hashlib.sha256((args.run/'source_manifest.json').read_bytes()).hexdigest(),
    recorded_rows=len(rows),partial_lines=dict(commands=command_partial,onboard=row_partial,detectors=detector_partial),
    command_topics=dict(command_topics),raw_frames=dict(collections.Counter(str(r['data']['coordinate_frame']) for r in raw)),
    raw_header_to_recorder_receipt_s=stats(r['stamp']-capture(r['data']) for r in raw if capture(r['data']) is not None),
    raw_header_phases=phases,sensors=motions,detectors=detector_stats,
    avoidance_unique_decisions=len(decisions),avoidance_states=dict(collections.Counter(r['detail']['state'] for r in decisions)),
    first_uncertified_braking=next((r for r in decisions if r['detail'].get('braking_clearance_available') is False),None),
    first_observed_clearance_below_070=next((r for r in decisions if isinstance(r['detail'].get('observed_clearance_m'),(int,float)) and r['detail']['observed_clearance_m']<.7),None),
    final=dict(stamp=last['stamp'],mission=last.get('mission'),flight=last.get('flight'),result=last.get('result'),avoidance=last.get('avoidance')) if last else None,
    limits=['Raw command header stamps are controller transmission stamps.',
            'flight_commands stamp is this independent recorder callback time, not the world callback.',
            'Simulator schedules reception .4 s after its own callback; that callback time is not recorded here.',
            'Avoidance detail has no decision capture timestamp; recorded_stamp is a recorder sample of cached detail.',
            'Detector events are object-level generated observations; their rates cannot qualify rendered images.',
            'This report does not use independent simulator truth for drone decisions.'])
for name in ('run.json','navigation_grade.json'):
    path=args.run/name
    report[name]=json.loads(path.read_text()) if path.exists() else None
args.out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('recorded_rows','command_topics','raw_header_to_recorder_receipt_s','raw_header_phases','avoidance_states','final')},indent=2))
