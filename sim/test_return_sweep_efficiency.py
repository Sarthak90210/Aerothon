"""Exercise an empty live-stage sweep: anticlockwise, then clockwise, once."""
import math

import py_trees

from test_return_gate_search import Clock, HFOV, World
from mission_bt.mission_tree import FindReturnBanner


def shortest_travel(headings):
    return sum(abs(math.atan2(math.sin(b-a), math.cos(b-a)))
               for a, b in zip(headings, headings[1:]))


def turns(headings):
    """Signed shortest-way turn between consecutive distinct headings."""
    out = []
    for a, b in zip(headings, headings[1:]):
        d = math.atan2(math.sin(b-a), math.cos(b-a))
        if abs(d) > 1e-6:
            out.append(d)
    return out


def test_empty_full_circle_turns_anticlockwise_then_clockwise():
    """The operator's search (20 Oct): yaw anticlockwise, then clockwise.
    Every 30 deg view is still seen; the turn reverses once, and the total
    stays far below the old left/right alternation's 1260 deg."""
    mav = World([], start=(14.5, -2.0, math.pi))
    leaf = FindReturnBanner(mav, alt=5.0, clock=Clock(), hfov_rad=HFOV)
    leaf.initialise()
    for _ in range(4000):
        assert leaf.update() == py_trees.common.Status.RUNNING
        if leaf._second_look_done:
            break
    else:
        raise AssertionError('first complete sweep did not finish')
    headings = [g[3] for g in mav.gotos]
    distinct = set(round(h, 5) for h in headings)
    assert len(distinct) == 12, 'retain all twelve observed headings'
    signs = [1 if d > 0 else -1 for d in turns(headings)]
    assert signs and signs[0] == 1, 'starts anticlockwise'
    reversals = sum(1 for a, b in zip(signs, signs[1:]) if a != b)
    assert reversals == 1 and signs[-1] == -1, 'one reversal, ending clockwise'
    assert max(abs(d) for d in turns(headings)) < math.pi - 0.1, (
        'every step is unambiguous, so the aircraft turns the commanded way')
    assert shortest_travel(headings) <= 3*math.pi


def test_initial_view_is_preserved_at_arbitrary_yaw():
    for yaw in (-3.05, 0.0, 2.8):
        mav = World([], start=(14.5, -2.0, yaw))
        leaf = FindReturnBanner(mav, clock=Clock())
        leaf.initialise()
        leaf.update()
        assert abs(math.atan2(math.sin(mav.gotos[-1][3]-yaw),
                              math.cos(mav.gotos[-1][3]-yaw))) < 1e-9


def test_a_hung_board_is_looked_for_down_after_the_banner_tilt():
    """r5: every return sighting was cut off at the bottom at -20 deg; the
    second look goes down to -45 deg, never level, for a hung board."""
    assert FindReturnBanner._second_tilt("BANNER") == "BANNER_DOWN"
    assert FindReturnBanner._second_tilt("BANNER_DOWN") == "BANNER"
    assert FindReturnBanner._second_tilt("FORWARD") == "BANNER"
    assert FindReturnBanner._second_tilt("GROUND") == "BANNER"


def test_a_flown_sweep_pans_at_its_yaw_rate_instead_of_snapping():
    """22 Oct (shipped_20kmh_r6): each 30 deg step snapped at ~44 deg/s and
    bounced back. At yaw_rate_rad_s the commanded heading never jumps by more
    than the rate allows between ticks, and the sweep still sees every view."""
    from mission_bt.mission_tree import ramp_yaw
    rate = math.radians(15.0)
    mav = World([], start=(14.5, -2.0, math.pi))
    leaf = FindReturnBanner(mav, alt=5.0, clock=Clock(), hfov_rad=HFOV, yaw_rate_rad_s=rate)
    leaf.initialise()
    for _ in range(20000):
        assert leaf.update() == py_trees.common.Status.RUNNING
        if leaf._second_look_done:
            break
    else:
        raise AssertionError('first complete sweep did not finish')
    steps = [abs(math.atan2(math.sin(b[3]-a[3]), math.cos(b[3]-a[3])))
             for a, b in zip(mav.gotos, mav.gotos[1:])]
    assert max(steps) <= rate * 0.5 + 1e-9, math.degrees(max(steps))
    assert len({round(h, 5) for h in leaf.headings}) == 12
    assert ramp_yaw(0.0, 1.0, math.inf, 0.0) == 1.0, 'unlimited rate is the old instant command'
    assert abs(ramp_yaw(3.1, -3.1, rate, 0.1) - (3.1 + rate * 0.1)) < 1e-9, 'short way round'


def test_a_near_return_board_in_front_of_the_outbound_banner_is_not_excluded():
    """shipped_20kmh_r7: the return board 4-5 m away was refused 374 times as
    the outbound banner, which stood 10-13 m behind it on nearly the same
    line. Area ranging only overestimates, so a board ranged well short of
    the outbound banner is a nearer one."""
    leaf = FindReturnBanner(World([], start=(17.1, -4.6, math.pi)), clock=Clock())
    ob = (8.3, -0.6)
    # The return board: 4.5 m dead ahead from the stand-off.
    assert not leaf._toward(ob, 17.1, -4.6, math.pi, 4.5)
    # The outbound banner itself, ranged 7 m past its true 13 m: still excluded.
    x, y = ob[0] + 13.0, ob[1]
    assert leaf._toward(ob, x, y, math.pi, 20.0)
    # ...and ranged about right.
    assert leaf._toward(ob, x, y, math.pi, 12.5)
