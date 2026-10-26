"""Red seen outside the supplied delivery zone is not a restricted zone.

Restricted zones lie inside the delivery zone. In r11 (24 Oct 2026) a tilted
frame during the first 20 km/h search leg confirmed two red boxes at x 13-16,
short of the zone (x >= 17), and the gate advance refused its destination
(13.1, -4.4) as inside a red zone. The mission now keeps only rectangles that
touch the supplied zone, and everything when no zone was supplied.

    source /opt/ros/jazzy/setup.bash
    python3 -m pytest sim/test_red_outside_delivery_zone.py -v
"""
import json
from types import SimpleNamespace

from std_msgs.msg import String

from mission_bt.detector_timing import DetectorTiming
from mission_bt.mav_commander import Mav, inside_delivery_zone

ZONE = (17.0, 61.0, -12.0, 12.0)
R11_FALSE = [[13.0, 16.0, -2.0, 1.0], [13.0, 16.0, -3.0, 0.0]]
REAL = [39.0, 42.0, -2.0, 1.0]


def consumer(zone):
    clock = SimpleNamespace(now=lambda: SimpleNamespace(nanoseconds=int(2e9)))
    return SimpleNamespace(node=SimpleNamespace(get_clock=lambda: clock),
                           detector_timing={'red': DetectorTiming()},
                           delivery_zone_local=zone)


def send(mav, confirmed, provisional=()):
    Mav._on_redzone(mav, String(data=json.dumps(dict(
        status='RED', capture_stamp=1.9, processed_stamp=2.,
        exclusions=confirmed, provisional_exclusions=list(provisional)))))


def test_r11_false_boxes_short_of_the_zone_are_dropped():
    mav = consumer(ZONE)
    send(mav, R11_FALSE + [REAL])
    assert mav.confirmed_exclusions == [tuple(REAL)]
    assert mav.exclusions == [tuple(REAL)]


def test_provisional_red_outside_the_zone_is_dropped_too():
    mav = consumer(ZONE)
    send(mav, [], provisional=[R11_FALSE[0], REAL])
    assert mav.provisional_exclusions == [tuple(REAL)]
    assert mav.exclusions == [tuple(REAL)]


def test_a_box_straddling_the_zone_edge_is_kept():
    edge = (15.5, 18.0, -1.0, 1.0)
    assert inside_delivery_zone([edge], ZONE) == [edge]
    corner = (60.0, 63.0, 11.0, 14.0)
    assert inside_delivery_zone([corner], ZONE) == [corner]


def test_beside_the_zone_in_y_is_dropped():
    assert inside_delivery_zone([(30.0, 33.0, 13.0, 15.0), (30.0, 33.0, -15.0, -12.5)], ZONE) == []


def test_without_a_supplied_zone_every_box_is_kept():
    mav = consumer(None)
    send(mav, R11_FALSE + [REAL])
    assert len(mav.exclusions) == 3
