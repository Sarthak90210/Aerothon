"""The organisers' clarifications, as checks.

Banners carry no text, their shades arrive as HEX before the flight, they may
be ground-mounted or suspended, and the QR must be matched by appearance
because it is unsettled whether it encodes anything. Each check here fails on
the behaviour that preceded the clarification, so a pass means the change is
actually in place rather than merely written down.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))

from perception_banner import colours                                # noqa: E402
from perception_qr import qr_appearance                              # noqa: E402


# ---- the supplied colours ----------------------------------------------- #

def test_a_hex_colour_becomes_a_hue_band_around_itself():
    hue, sat, val = colours.hsv_of('#07A03D')
    assert 50 <= hue <= 80, 'that green should land in the green hues'
    (lo, hi), = colours.ranges('#07A03D')
    assert lo[0] < hue < hi[0]
    # Saturation and value are left wide on purpose: wear, shade and exposure
    # move them, and pinning them to the supplied colour rejects the banner.
    assert lo[1] <= colours.DEFAULT_S_FLOOR and hi[1] == 255
    assert lo[2] <= colours.DEFAULT_V_FLOOR and hi[2] == 255


def test_a_red_hue_window_wraps_the_circle_into_two_bands():
    bands = colours.ranges('#C4161C')
    assert len(bands) == 2, 'red sits at 0/180 and needs both sides'
    assert any(int(lo[0]) == 0 for lo, _ in bands)
    assert any(int(hi[0]) == 179 for _, hi in bands)


@pytest.mark.parametrize('bad', ['', 'green', '#12345', '#GGGGGG', None, 42,
                                 '#1234567'])
def test_anything_that_is_not_a_hex_colour_is_refused(bad):
    with pytest.raises(ValueError):
        colours.parse_hex(bad)


def test_an_unknown_colour_name_is_refused_rather_than_dropped():
    # A colour the aircraft silently ignores is worse than one it rejects:
    # the operator believes it was taken.
    with pytest.raises(ValueError):
        colours.validate({'green': '#07A03D', 'turquoise': '#00FFEE'})
    assert colours.validate({'green': '#07a03d'}) == {'green': '#07A03D'}


def test_the_supplied_green_matches_that_green_and_not_the_orange():
    import cv2
    green = np.full((8, 8, 3), colours.parse_hex('#07A03D')[::-1], np.uint8)
    orange = np.full((8, 8, 3), colours.parse_hex('#EB5A0A')[::-1], np.uint8)
    bands = colours.ranges('#07A03D')
    assert colours.mask(cv2.cvtColor(green, cv2.COLOR_BGR2HSV), bands).all()
    assert not colours.mask(cv2.cvtColor(orange, cv2.COLOR_BGR2HSV), bands).any()


# ---- appearance-first QR ------------------------------------------------- #

def marker(seed, side=160):
    """A printed-looking marker: a coarse random pattern with a quiet zone."""
    rng = np.random.default_rng(seed)
    cells = rng.integers(0, 2, size=(10, 10), dtype=np.uint8) * 255
    import cv2
    body = cv2.resize(cells, (side-40, side-40), interpolation=cv2.INTER_NEAREST)
    frame = np.full((side, side), 255, np.uint8)
    frame[20:side-20, 20:side-20] = body
    return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)


QUAD = np.array([[20, 20], [139, 20], [139, 139], [20, 139]], dtype=np.float32)


def test_the_same_marker_matches_itself_through_a_turn_and_a_rescale():
    import cv2
    first = qr_appearance.signature(marker(7), QUAD)
    bigger = cv2.resize(marker(7), (320, 320), interpolation=cv2.INTER_LINEAR)
    turned = cv2.rotate(bigger, cv2.ROTATE_90_CLOCKWISE)
    second = qr_appearance.signature(
        turned, np.array([[40, 40], [279, 40], [279, 279], [40, 279]], np.float32))
    same, score = qr_appearance.same_marker(first, second)
    assert same, f'the same code at another size and turn scored {score}'


def test_a_different_marker_does_not_match():
    first = qr_appearance.signature(marker(7), QUAD)
    other = qr_appearance.signature(marker(99), QUAD)
    same, score = qr_appearance.same_marker(first, other)
    assert not same, f'two different codes scored {score}'
    assert score < qr_appearance.DEFAULT_THRESHOLD


def test_a_marker_too_small_to_rectify_yields_no_signature():
    tiny = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.float32)
    assert qr_appearance.signature(marker(7), tiny) is None
    # ...and an absent signature can never match anything.
    assert qr_appearance.agreement(None, qr_appearance.signature(marker(7), QUAD)) == 0.0


# ---- the arena the organisers describe ---------------------------------- #

def test_the_banner_is_built_with_no_lettering_but_keeps_its_white_border():
    import materialize_world as MW
    panel = MW.banner_geometry(0, 2.805)
    assert 'banner_front_frame_top' in panel, 'the 3-inch border is the identity'
    assert 'banner_front_0"' not in panel, 'the banners carry no text'
    lettered = MW.banner_geometry(0, 2.805, lettered=True)
    assert 'banner_front_0"' in lettered, 'the old panel must still be buildable'


def test_a_ground_banner_lies_flat_with_a_border_and_no_collision():
    import materialize_world as MW
    laid = MW.ground_banner_geometry(0)
    assert 'ground_banner_panel' in laid and 'ground_banner_border_n' in laid
    # A sheet on the ground is not something the aircraft can hit; a collision
    # box here would put a phantom obstacle across the corridor mouth.
    assert 'collision' not in laid


def test_a_supplied_hex_paints_the_banner_it_was_supplied_for():
    import world_spec as W
    ambient, diffuse = W.print_colour('#07A03D')
    assert diffuse == pytest.approx((0.0275, 0.6275, 0.2392), abs=1e-3)
    assert all(a < d for a, d in zip(ambient, diffuse) if d > 0)


@pytest.mark.parametrize('placement', ['suspended', 'ground', 'both'])
def test_every_banner_placement_the_organisers_allow_validates(placement):
    import world_spec as W
    spec = W.normalise({'banner': {'placement': placement}})
    assert W.validate(spec)[0] == []


def test_an_unknown_placement_or_colour_is_refused():
    import world_spec as W
    errors, _ = W.validate(W.normalise({'banner': {'placement': 'sideways'}}))
    assert any('placement' in e for e in errors)
    errors, _ = W.validate(W.normalise({'banner': {'colours': {'green': 'teal'}}}))
    assert any('not #RRGGBB' in e for e in errors)


def test_the_flown_worlds_carry_no_fake_green_banners():
    """The organisers' arena has nothing green in it but the banners.

    One world keeps the decoys on purpose, so "reject a plain coloured sheet"
    is still measured against something rather than assumed.
    """
    planted = {p.stem: len(json.loads(p.read_text()).get('decoys') or [])
               for p in sorted((ROOT/'sim/worlds').glob('*.json'))}
    assert planted.pop('banner_decoys') > 0, 'the negative control needs decoys'
    assert not {k: v for k, v in planted.items() if v}, 'flown worlds must have none'


def test_the_three_placement_cases_exist_and_differ_only_in_placement():
    specs = {name: json.loads((ROOT/f'sim/worlds/{name}.json').read_text())
             for name in ('banner_ground', 'banner_suspended', 'banner_both')}
    assert {s['banner']['placement'] for s in specs.values()} == {
        'ground', 'suspended', 'both'}
    for spec in specs.values():
        assert spec['banner']['lettered'] is False
        assert spec['banner']['colours']['green'].startswith('#')
        assert spec['decoys'] == []
