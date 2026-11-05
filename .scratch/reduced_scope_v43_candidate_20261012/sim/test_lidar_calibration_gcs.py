"""The GCS's lidar calibration mode, end to end without a lidar.

Two boxes -- one ahead of the nose, one to port -- in the driver's raw scan
give the mount; the GCS refuses it in the air, refuses captures that do not
agree, and sends what it measured to scan_mount, which applies it at once and
keeps it across a restart.

    python3 -m pytest sim/test_lidar_calibration_gcs.py -v
"""
import json
import math
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from test_scan_mount import raw_scan                                   # noqa: E402
from gcs_aggregator import lidar_calibration as L                      # noqa: E402
from mission_bringup.scan_mount import mount, parse_mount              # noqa: E402


@pytest.fixture
def aggregator(tmp_path):
    with patch('rclpy.node.Node.__init__', return_value=None), \
         patch('rclpy.node.Node.create_subscription'), \
         patch('rclpy.node.Node.create_publisher'), \
         patch('rclpy.node.Node.create_client'), \
         patch('rclpy.node.Node.create_timer'), \
         patch('rclpy.node.Node.declare_parameter'), \
         patch('rclpy.node.Node.get_parameter',
               return_value=MagicMock(value=str(tmp_path/'presets.json'))), \
         patch('rclpy.node.Node.get_logger'):
        from gcs_aggregator.aggregator import Aggregator
        node = Aggregator()
    node.pub_lidar_mount = MagicMock()
    return node


def _capture(agg, where, body_deg, yaw, mirrored):
    agg._on_scan_raw(raw_scan(body_deg, yaw, mirrored))
    return agg._dispatch("lidar_cal_capture", {"where": where})


@pytest.mark.parametrize("yaw,mirrored", [(0.0, False), (37.0, False),
                                          (-135.0, True), (90.0, True)])
def test_two_boxes_give_the_mount_and_apply_sends_it(aggregator, yaw, mirrored):
    assert _capture(aggregator, "ahead", 0.0, yaw, mirrored) == ("accepted", "")
    assert aggregator.state["lidar_cal"]["result"] is None, "one box is not a mount"
    assert _capture(aggregator, "port", 90.0, yaw, mirrored) == ("accepted", "")
    res = aggregator.state["lidar_cal"]["result"]
    assert res["ok"] and res["mirrored"] is mirrored
    assert abs(((res["yaw_deg"] - yaw) + 180) % 360 - 180) < 1.0
    assert aggregator._dispatch("lidar_cal_apply", {}) == ("accepted", "")
    (msg,), _ = aggregator.pub_lidar_mount.publish.call_args
    sent = json.loads(msg.data)
    assert sent == {"yaw_deg": res["yaw_deg"], "mirrored": mirrored}
    # What it sends is what scan_mount turns into the nose and port.
    y, m = parse_mount(sent)
    for body in (0.0, 90.0, -60.0):
        s = mount(raw_scan(body, yaw, mirrored), math.radians(y), m)
        assert L.nearest_bearing(s)[0] == pytest.approx(body, abs=1.0)


def test_captures_that_disagree_are_not_applied(aggregator):
    _capture(aggregator, "ahead", 0.0, 0.0, False)
    _capture(aggregator, "port", 40.0, 0.0, False)     # the 'port' box was 40 deg off
    res = aggregator.state["lidar_cal"]["result"]
    assert not res["ok"] and "square" in res["reason"]
    result, reason = aggregator._dispatch("lidar_cal_apply", {})
    assert result == "rejected"
    aggregator.pub_lidar_mount.publish.assert_not_called()


def test_no_calibration_in_the_air_and_none_without_a_raw_scan(aggregator):
    assert aggregator._dispatch("lidar_cal_capture", {"where": "ahead"})[0] == "rejected"
    aggregator.state["mission"]["armed"] = True
    _ = aggregator._on_scan_raw(raw_scan(0.0, 0.0, False))
    result, reason = aggregator._dispatch("lidar_cal_capture", {"where": "ahead"})
    assert result == "rejected" and "disarmed" in reason
    assert aggregator._dispatch("lidar_cal_apply", {})[0] == "rejected"


def test_a_stale_raw_scan_is_not_captured(aggregator):
    aggregator._on_scan_raw(raw_scan(0.0, 0.0, False))
    scan, t = aggregator._scan_raw
    aggregator._scan_raw = (scan, t - 5.0)
    assert aggregator._dispatch("lidar_cal_capture", {"where": "ahead"})[0] == "rejected"


def test_reset_clears_the_captures(aggregator):
    _capture(aggregator, "ahead", 0.0, 0.0, False)
    aggregator._dispatch("lidar_cal_reset", {})
    cal = aggregator.state["lidar_cal"]
    assert cal["captures"] == {"ahead": None, "port": None} and cal["result"] is None


def test_the_panel_sees_the_live_nearest_return_in_both_frames(aggregator):
    aggregator._on_scan_raw(raw_scan(0.0, 37.0, False))
    aggregator._on_scan(raw_scan(0.0, 0.0, False))
    aggregator._lidar_cal_refresh()
    cal = aggregator.state["lidar_cal"]
    assert cal["raw_fresh"]
    assert cal["raw_nearest"][0] == pytest.approx(-37.0, abs=1.0)
    assert cal["body_nearest"][0] == pytest.approx(0.0, abs=1.0)


# ---- scan_mount applies it live and keeps it ---------------------------- #

def _scan_mount(tmp_path):
    from mission_bringup import scan_mount as SM
    node = types.SimpleNamespace(
        yaw=0.0, mirrored=False, mount_file=str(tmp_path / "mount.json"),
        source="launch arguments", pub_applied=MagicMock(),
        get_logger=lambda: MagicMock())
    for name in ("_on_mount", "_report", "_load_saved"):
        setattr(node, name, getattr(SM.ScanMount, name).__get__(node))
    return node


def test_scan_mount_applies_a_gcs_mount_at_once_and_keeps_it(tmp_path):
    node = _scan_mount(tmp_path)
    node._on_mount(types.SimpleNamespace(data=json.dumps({"yaw_deg": 37.0, "mirrored": True})))
    assert node.yaw == pytest.approx(math.radians(37.0)) and node.mirrored is True
    (msg,), _ = node.pub_applied.publish.call_args
    assert json.loads(msg.data)["source"] == "GCS calibration"
    restarted = _scan_mount(tmp_path)
    restarted._load_saved()
    assert restarted.yaw == pytest.approx(math.radians(37.0)) and restarted.mirrored
    assert "saved calibration" in restarted.source


@pytest.mark.parametrize("bad", [{"yaw_deg": 400.0, "mirrored": False},
                                 {"yaw_deg": 10.0, "mirrored": "yes"}, {"mirrored": True}])
def test_scan_mount_refuses_a_bad_mount(tmp_path, bad):
    node = _scan_mount(tmp_path)
    node._on_mount(types.SimpleNamespace(data=json.dumps(bad)))
    assert node.yaw == 0.0 and node.mirrored is False
    assert not os.path.exists(node.mount_file)
