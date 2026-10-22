"""A narrow slalom slot: plan through it at the hard clearance, sidestep back
into it when a few cm inside, and still refuse beyond that.

shipped_20kmh_r9b: the return lane's first slalom block leaves a 0.98 m slot
against the simulation's 2 x 0.45 m. The aircraft sat 4 cm off the slot's
centre line, 1 cm inside the clearance; FastConnectedPlanner refused every
tick ("aircraft lacks required surface clearance") and the grid's 2.5 cm
sampling reserve left no lattice cell in the 3 cm band that remained, so the
navigator cycled BLOCKED/BACKOFF and gave up STUCK at x=12.24.
"""
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/aerothon_avoidance/avoidance'))
from avoidance.fast_connected_planner_candidate import FastConnectedPlanner  # noqa: E402

CLEARANCE = 0.45


def rect(x0, x1, y0, y1):
    return [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]


def slalom(offset):
    """Body frame, x forward, y left; the aircraft `offset` m left of slot 1's
    centre line. Walls 2 m apart; block A beside the aircraft leaves the
    0.98 m slot 1; block B 2.2 m ahead leaves slot 2 on the right."""
    dy = -offset
    segs = [((-3.0, 0.49 + dy), (8.0, 0.49 + dy)), ((-3.0, -1.51 + dy), (8.0, -1.51 + dy))]
    segs += rect(-0.6, 0.6, -1.51 + dy, -0.49 + dy)       # block A: slot 1 is y -0.49..0.49
    segs += rect(2.2, 2.6, -0.49 + dy, 0.49 + dy)         # block B: slot 2 is y -1.51..-0.49
    bearings = np.linspace(-math.pi, math.pi, 1441)
    ranges = []
    for a in bearings:
        dx, dyr = math.cos(a), math.sin(a)
        best = 12.0
        for (x0, y0), (x1, y1) in segs:
            ex, ey = x1 - x0, y1 - y0
            den = dx * ey - dyr * ex
            if abs(den) < 1e-12:
                continue
            t = (x0 * ey - y0 * ex) / den
            u = (x0 * dyr - y0 * dx) / den
            if t > 0 and 0 <= u <= 1:
                best = min(best, t)
        ranges.append(best)
    return bearings, np.array(ranges)


def planner(offset):
    p = FastConnectedPlanner(CLEARANCE, clearance_floor=CLEARANCE, occupied_radius=0.025)
    p.observe(*slalom(offset))
    return p


def test_a_slot_with_no_lattice_cell_in_the_reserve_band_is_still_planned():
    p = planner(0.02)                               # 0.47 m clearance, inside 0.475
    assert p.distances([(0, 0)])[0] >= CLEARANCE
    path = p.plan(0.0)
    assert path, p.reason
    assert all(p.segment_clear(a, b) for a, b in zip(path, path[1:]))
    dense = np.concatenate([np.linspace(a, b, 400) for a, b in zip(path, path[1:])])
    assert p.distances(dense).min() >= CLEARANCE - 1e-9, 'no clearance given away'
    assert max(x for x, _ in path) > 2.6, 'route goes past block B'


def test_a_few_cm_inside_the_clearance_sidesteps_back_toward_the_centre():
    p = planner(0.06)                               # 0.43 m from the left wall
    assert p.plan(0.0) == []
    assert p.recentre is not None
    ux, uy = p.recentre
    assert uy < -0.9, f'sidestep right, away from the near wall: {p.recentre}'
    assert p.distances([(0.03 * ux, 0.03 * uy)])[0] > p.distances([(0, 0)])[0]


def test_well_inside_the_clearance_is_still_refused_without_a_sidestep():
    p = planner(0.10)                               # 0.39 m: beyond the slack
    assert p.plan(0.0) == []
    assert p.recentre is None
