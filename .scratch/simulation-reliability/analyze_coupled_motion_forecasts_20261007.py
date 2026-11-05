"""Independent forecast comparison; never imported by flight software."""
import bisect,json,math
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_coupled_motion_forecasts_20261007'
rectangles=[(-.1,9.1,1.6,1.7),(-.1,9.1,-1.7,-1.6)]
for u,v,w,d,degrees in [(2.,.9,.4,1.3,0),(4.5,-.8,.4,1.4,15),(7.,.7,.5,1.2,0)]:
    a=math.radians(degrees);du=(abs(w*math.cos(a))+abs(d*math.sin(a)))/2
    dv=(abs(w*math.sin(a))+abs(d*math.cos(a)))/2
    rectangles.append((9-u-du,9-u+du,-v-dv,-v+dv))
def clearance(point):
    x,y=point
    return min(math.hypot(max(x0-x,0,x-x1),max(y0-y,0,y-y1)) for x0,x1,y0,y1 in rectangles)
summary=[]
for kind,seed in [('dirty',0),('late',1)]:
    actual=json.loads((out/f'{kind}_s{seed}.json').read_text())['rows']
    forecasts=json.loads((out/f'{kind}_s{seed}_forecasts.json').read_text())['records']
    stamps=[row['stamp'] for row in actual]
    first=next(row for row in actual if row['independent_preintegration_clearance_m']<.7)
    comparisons=[]
    for record in forecasts:
        before=record['before'];co,si=math.cos(before['yaw']),math.sin(before['yaw'])
        command=[record['detail']['cmd_vx'],record['detail']['cmd_vy_left']]
        accepted=[prediction for prediction in record['predictions'] if prediction['clear'] is True
                  and math.dist(prediction['command'],command)<.006]
        if not accepted:continue
        prediction=accepted[-1]
        for interval,x,y in prediction['points_body']:
            endpoint=interval+.05
            # Until physical receipt, future commands from later ticks cannot
            # affect motion. Future unobserved gusts can, so this is empirical.
            if endpoint>.4+1e-8:continue
            stamp=prediction['sample_epoch']+endpoint
            index=bisect.bisect_left(stamps,stamp)
            if index==len(actual) or abs(stamps[index]-stamp)>.026:continue
            projected=(before['pose'][0]+co*x-si*y,before['pose'][1]+si*x+co*y)
            observed=actual[index]['pose']
            comparisons.append(dict(forecast_stamp=before['clock_s'],endpoint_s=endpoint,
                predicted_world_xy=projected,actual_world_xy=observed,
                error_m=math.dist(projected,observed),predicted_clearance_m=clearance(projected),
                actual_clearance_m=clearance(observed),
                measured_velocity=before['ground_world'],estimated_disturbance=before['wind_world'],
                estimated_disturbance_rate=before['wind_rate_world']))
    summary.append(dict(kind=kind,seed=seed,first_recorded_clearance_loss=first,
        prefix_comparisons=len(comparisons),maximum_prefix_error_m=max(r['error_m'] for r in comparisons),
        worst_prefix=max(comparisons,key=lambda r:r['error_m']),
        falsely_clear_prefixes=[r for r in comparisons if r['actual_clearance_m']<.7 and r['predicted_clearance_m']>=.725][-5:]))
report=dict(cases=summary,simulator_geometry_used_only_for_evaluation=True,
    controller_changed=False,future_disturbance_bound_established=False,
    time_basis='Original diagnostic labels store interval starts; endpoints add 0.05 s')
(out/'forecast_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([dict(kind=r['kind'],first_loss_s=r['first_recorded_clearance_loss']['stamp'],
    maximum_prefix_error_m=r['maximum_prefix_error_m'],false_clear_count=len(r['falsely_clear_prefixes'])) for r in summary]))
