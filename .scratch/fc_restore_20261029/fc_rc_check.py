"""Read-only: RC_CHANNELS rate and values (ch1-9, rssi) and SERVO_OUTPUT_RAW output 5, 10 s at the router."""
import time
from pymavlink import mavutil
m = mavutil.mavlink_connection("udpout:127.0.0.1:14550", source_system=250, source_component=191, dialect="ardupilotmega")
n, last, s5 = 0, None, set()
t0 = time.time()
while time.time() - t0 < 10:
    m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
    msg = m.recv_match(type=["RC_CHANNELS", "SERVO_OUTPUT_RAW"], blocking=True, timeout=0.5)
    if not msg or msg.get_srcSystem() != 1:
        continue
    if msg.get_type() == "RC_CHANNELS":
        n += 1
        last = msg
    else:
        s5.add(msg.servo5_raw)
print(f"RC_CHANNELS {n / 10:.1f} Hz", end="; ")
if last:
    print("chancount", last.chancount, "rssi", last.rssi, "ch1-9",
          [getattr(last, f"chan{i}_raw") for i in range(1, 10)])
print("output 5 values seen:", sorted(s5))
