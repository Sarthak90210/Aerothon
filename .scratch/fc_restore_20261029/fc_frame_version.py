"""Read-only: the MAVLink version (first byte 0xFD v2 / 0xFE v1) of the FC's frames at the router, and their rate."""
import time
from pymavlink import mavutil
m = mavutil.mavlink_connection("udpout:127.0.0.1:14550", source_system=250, source_component=191, dialect="ardupilotmega")
count, start = {}, time.time()
while time.time() - start < 10:
    m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
    msg = m.recv_match(blocking=True, timeout=1)
    if msg is None or msg.get_srcSystem() != 1:
        continue
    key = (msg.get_srcComponent(), msg.get_type(), hex(msg.get_msgbuf()[0]))
    count[key] = count.get(key, 0) + 1
for k, v in sorted(count.items()):
    print(k, v, "in 10 s")
