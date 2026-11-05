"""Locate the V40 split clearance loss and compare it with the planner's belief.

Independent geometry against the recorded controller detail at the same
moment: what surface, what phase, what the planner had certified, and whether
any deadline, scan age or motion estimate was degraded there. Writes a
diagnosis into the run directory; changes no grade.

    python3 .scratch/simulation-reliability/diagnose_v40_split_clearance_20261010.py RUN_DIR
"""
import bisect
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root/'sim'), str(root/'scripts')]
from check_track import lanes, to_lane, rect_gap                      # noqa: E402


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def gaps(track, layout):
    """Every armed airborne sample's distance to each wall and obstacle.

    The track is `evaluation_track.json`, the exact home-local samples the
    grader measured, so these distances are the graded ones.
    """
    hx, hy = layout.get('home_world', [0, 0])
    out = []
    for r in track:
        if not r['armed'] or r['z'] <= .3:
            continue
        for index, lane in enumerate(lanes(layout)):
            u, v = to_lane(r, layout, lane)
            if 0 <= u <= lane[3] and abs(v) <= lane[4]/2 and r['z'] < lane[5]:
                out.append((lane[4]/2-abs(v), r, f'lane {index} wall', dict(u=u, v=v)))
        for index, obstacle in enumerate(layout.get('obstacles', [])):
            if r['z'] < obstacle['h']+.3:
                poly = [(x-hx, y-hy) for x, y in obstacle['poly']]
                out.append((rect_gap(poly, r['x'], r['y']), r, f'obstacle {index}',
                            dict(height_m=obstacle['h'], poly=obstacle['poly'])))
    return out


def controller_detail(rows, times, stamp, window=1.5):
    near = []
    for r in rows:
        if abs(r['stamp']-stamp) > window:
            continue
        detail = r.get('avoidance') or {}
        near.append(dict(stamp=r['stamp'], phase=r.get('mission'),
                         observed_clearance_m=detail.get('observed_clearance_m'),
                         state=detail.get('state'), front_m=detail.get('front_m'),
                         side_left_m=detail.get('side_left_m'), side_right_m=detail.get('side_right_m'),
                         scan_age_s=detail.get('scan_age_s'),
                         computation_s=detail.get('motion_computation_elapsed_s'),
                         budget_s=detail.get('motion_computation_budget_s'),
                         certified_clearance_m=detail.get('certified_clearance_m'),
                         target=detail.get('target'), corridor_entered=detail.get('corridor_entered'),
                         corridor_exited=detail.get('corridor_exited')))
    return near


def phase_of(rows, times, stamp):
    i = bisect.bisect_right(times, stamp)-1
    return (rows[i].get('mission') if i >= 0 else None)


def main():
    out = Path(sys.argv[1])
    layout = json.loads((out/'layout.json').read_text())
    track = json.loads((out/'evaluation_track.json').read_text())
    rows = read(out/'onboard.jsonl')
    times = [r['stamp'] for r in rows]
    measured = gaps(track, layout)
    worst = min(measured, key=lambda item: item[0])
    below = sorted((item for item in measured if item[0] < .70),
                   key=lambda item: item[1]['t'])
    episodes = []
    for value, sample, surface, extra in below:
        if episodes and episodes[-1]['surface'] == surface and sample['t']-episodes[-1]['last_t'] <= .5:
            episode = episodes[-1]
            episode['last_t'] = sample['t']
            episode['samples'] += 1
            if value < episode['minimum_clearance_m']:
                episode.update(minimum_clearance_m=value, minimum_t=sample['t'],
                               position=[sample['x'], sample['y'], sample['z']])
        else:
            episodes.append(dict(surface=surface, first_t=sample['t'], last_t=sample['t'],
                                 samples=1, minimum_clearance_m=value, minimum_t=sample['t'],
                                 position=[sample['x'], sample['y'], sample['z']],
                                 phase=phase_of(rows, times, sample['t']), surface_detail=extra))
    detail = [r.get('avoidance') or {} for r in rows
              if (r.get('avoidance') or {}).get('motion_computation_elapsed_s') is not None]
    report = dict(
        run=str(out),
        minimum_clearance_m=worst[0], minimum_t=worst[1]['t'], surface=worst[2],
        surface_detail=worst[3],
        position=[worst[1]['x'], worst[1]['y'], worst[1]['z']],
        phase=phase_of(rows, times, worst[1]['t']),
        samples_below_threshold=len(below), episodes=episodes,
        controller_detail_near_minimum=controller_detail(rows, times, worst[1]['t']),
        recorded_controller_samples=len(detail),
        deadline_overruns=sum(d['motion_computation_elapsed_s'] >
                              d.get('motion_computation_budget_s', 1e9)+1e-9 for d in detail),
        max_computation_s=max((d['motion_computation_elapsed_s'] for d in detail), default=None),
        max_scan_age_s=max((d['scan_age_s'] for d in detail
                            if d.get('scan_age_s') is not None), default=None),
        min_planner_observed_clearance_m=min((d['observed_clearance_m'] for d in detail
                                              if d.get('observed_clearance_m') is not None),
                                             default=None),
        grade_unchanged=True)
    (out/'clearance_diagnosis.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items()
                      if k != 'controller_detail_near_minimum'}, indent=2))


if __name__ == '__main__':
    main()
