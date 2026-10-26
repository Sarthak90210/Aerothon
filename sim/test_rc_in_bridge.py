#!/usr/bin/env python3
"""Transmitter channels reach the runtime even when the FC reports chancount 0.

The aircraft, 25 Oct 2026: an ExpressLRS receiver in MAVLink mode on SERIAL2
(MAVLink2, 460800) sends the sticks as RC overrides. ArduPilot reported
RC_CHANNELS with chancount 0 and live values (channel 5 at 2000 us, seen in
Mission Planner), and MAVROS published /mavros/rc/in with no channels, so the
winch's channel 5, the transmitter test and its takeover switch saw nothing.

    python3 -m pytest sim/test_rc_in_bridge.py -v
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src", "aerothon_runtime"))
from aerothon_runtime.rc_in_bridge import decode_rc_channels  # noqa: E402


def payload(values, chancount, rssi=255, time_ms=123456):
    values = list(values) + [0xFFFF] * (18 - len(values))
    return struct.pack('<I18HBB', time_ms, *values, chancount, rssi)


AIRCRAFT = [1500, 1500, 989, 1500, 2000, 1000, 2000, 2000]   # as decoded on 25 Oct


def test_live_values_with_chancount_0_are_kept():
    channels, rssi = decode_rc_channels(payload(AIRCRAFT, 0))
    assert channels == AIRCRAFT
    assert channels[4] == 2000            # channel 5, the winch's
    assert rssi == 255


def test_a_reported_chancount_is_used_as_is():
    channels, _ = decode_rc_channels(payload(AIRCRAFT + [1500] * 8, 16))
    assert len(channels) == 16


def test_unused_channels_end_the_list():
    values = AIRCRAFT + [0] * 10
    assert decode_rc_channels(payload(values, 0))[0] == AIRCRAFT


def test_mavlink2_trimmed_payload_decodes():
    raw = payload(AIRCRAFT, 0, rssi=0).rstrip(b'\0')
    assert decode_rc_channels(raw)[0] == AIRCRAFT


def test_no_transmitter_gives_no_channels():
    assert decode_rc_channels(payload([], 0))[0] == []


def test_every_rc_consumer_reads_the_bridge():
    for path in ("src/aerothon_payload/winch_ctrl/winch_ctrl/winch_node.py",
                 "src/aerothon_runtime/aerothon_runtime/execution_node.py",
                 "src/aerothon_gcs/gcs_aggregator/gcs_aggregator/readiness_node.py"):
        text = open(os.path.join(ROOT, path), encoding="utf-8").read()
        subscriptions = re.findall(r"create_subscription\(\s*RCIn,\s*['\"]([^'\"]+)['\"]", text)
        assert subscriptions == ["/aerothon/rc/in"], (path, subscriptions)
    launch = open(os.path.join(ROOT, "src/aerothon_mission/mission_bringup/launch/mission2.launch.py"),
                  encoding="utf-8").read()
    assert "executable='rc_in_bridge'" in launch and "rc_bridge," in launch
