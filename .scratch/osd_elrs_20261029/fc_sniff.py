"""Read-only: 12 s of traffic through the router: who sends what, RC_CHANNELS
(chancount, rssi), RADIO_STATUS, and the FC's boot/status texts."""
import collections
import time
from pymavlink import mavutil

m = mavutil.mavlink_connection("udpout:127.0.0.1:14550", source_system=250,
                               source_component=191, dialect="ardupilotmega")
seen = collections.Counter()
last = {}
end = time.time() + 12
nexthb = 0
while time.time() < end:
    if time.time() > nexthb:
        m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
        nexthb = time.time() + 1
    msg = m.recv_match(blocking=True, timeout=0.5)
    if not msg or msg.get_type() == "BAD_DATA":
        continue
    key = (msg.get_srcSystem(), msg.get_srcComponent(), msg.get_type())
    seen[key] += 1
    last[key] = msg
    if msg.get_type() == "STATUSTEXT":
        print("  text", key[:2], msg.text)
for key, n in sorted(seen.items()):
    print(key, n)
for key, msg in last.items():
    if key[2] in ("RC_CHANNELS", "RADIO_STATUS", "RC_CHANNELS_OVERRIDE", "RC_CHANNELS_RAW", "HEARTBEAT") and key[:2] != (1, 1) or key[2] in ("RC_CHANNELS", "RADIO_STATUS"):
        d = msg.to_dict()
        print(key, {k: d[k] for k in list(d)[:12]})
