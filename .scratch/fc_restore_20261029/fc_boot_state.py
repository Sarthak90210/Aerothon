"""Read-only: FC uptime (SYSTEM_TIME), armed flag and the last STATUSTEXTs, through the router."""
import time
from pymavlink import mavutil
m = mavutil.mavlink_connection("udpout:127.0.0.1:14550", source_system=250, source_component=191, dialect="ardupilotmega")
st = hb = None
texts = []
end = time.time() + 6
while time.time() < end:
    m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
    msg = m.recv_match(blocking=True, timeout=0.5)
    if not msg or msg.get_srcSystem() != 1:
        continue
    if msg.get_type() == "SYSTEM_TIME":
        st = msg.time_boot_ms / 1000.0
    if msg.get_type() == "HEARTBEAT" and msg.get_srcComponent() == 1:
        hb = msg
    if msg.get_type() == "STATUSTEXT":
        texts.append(msg.text)
print("FC up", st, "s;", "ARMED" if hb and hb.base_mode & 128 else "disarmed", "mode", hb and hb.custom_mode)
for t in texts[-8:]:
    print("  FC:", t)
