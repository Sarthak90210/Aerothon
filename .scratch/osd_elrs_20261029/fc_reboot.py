"""Reboot the FC (MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN 1) through the router,
refusing unless disarmed; then wait for its heartbeat to come back."""
import sys
import time
from pymavlink import mavutil

m = mavutil.mavlink_connection("udpout:127.0.0.1:14550", source_system=250,
                               source_component=191, dialect="ardupilotmega")


def heartbeat(timeout):
    end = time.time() + timeout
    while time.time() < end:
        m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
        msg = m.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
        if msg and msg.get_srcSystem() == 1 and msg.get_srcComponent() == 1:
            return msg
    return None


hb = heartbeat(15)
if hb is None:
    sys.exit("no FC heartbeat through the router")
if hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED:
    sys.exit("refusing: the FC reports ARMED")
print("FC disarmed; rebooting", flush=True)
m.mav.command_long_send(1, 1, mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN, 0, 1, 0, 0, 0, 0, 0, 0)
ack = m.recv_match(type="COMMAND_ACK", blocking=True, timeout=3)
print("ack:", ack.result if ack else None, flush=True)
t0 = time.time()
time.sleep(4)
while time.time() - t0 < 60:
    msg = m.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
    m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
    if msg and msg.get_srcSystem() == 1 and msg.get_srcComponent() == 1:
        print(f"FC heartbeat back after {time.time() - t0:.0f} s", flush=True)
        break
else:
    sys.exit("FC heartbeat not back within 60 s")
end = time.time() + 8
while time.time() < end:
    t = m.recv_match(type="STATUSTEXT", blocking=True, timeout=1)
    if t:
        print("  FC:", t.text, flush=True)
