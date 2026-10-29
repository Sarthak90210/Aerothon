"""Read-only: the FC's heartbeats (who, armed, mode, status), a few servo/link
parameters and SERVO_OUTPUT_RAW output 5, through the router's GCS port.

    MAVLINK20=1 MAVLINK_DIALECT=ardupilotmega PYTHONPATH=pylib python3 fc_probe.py
"""
import time

from pymavlink import mavutil

m = mavutil.mavlink_connection("udpout:127.0.0.1:14550", source_system=250,
                               source_component=191, dialect="ardupilotmega")
seen = {}
end = time.time() + 8
while time.time() < end:
    m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
    msg = m.recv_match(blocking=True, timeout=0.5)
    if msg is None:
        continue
    t = msg.get_type()
    key = (msg.get_srcSystem(), msg.get_srcComponent(), t)
    seen[key] = seen.get(key, 0) + 1
    if t == "HEARTBEAT":
        armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        seen[("hb", msg.get_srcSystem(), msg.get_srcComponent())] = (
            f"type {msg.type} autopilot {msg.autopilot} base_mode {msg.base_mode:#x} "
            f"custom_mode {msg.custom_mode} system_status {msg.system_status} "
            f"{'ARMED' if armed else 'disarmed'}")
    if t == "SERVO_OUTPUT_RAW" and msg.get_srcSystem() == 1:
        seen["servo"] = [getattr(msg, f"servo{i}_raw") for i in range(1, 9)]
    if t == "STATUSTEXT":
        print("FC text:", msg.get_srcSystem(), msg.get_srcComponent(), msg.text, flush=True)
for k, v in sorted(seen.items(), key=str):
    print(k, v)

for name in ("SERVO5_FUNCTION", "MNT1_TYPE", "SERIAL5_PROTOCOL", "SERIAL5_BAUD",
             "SERIAL1_PROTOCOL", "SERIAL1_BAUD", "FRAME_CLASS", "ARMING_CHECK", "FORMAT_VERSION"):
    got = None
    for _ in range(3):
        m.mav.param_request_read_send(1, 1, name.encode(), -1)
        deadline = time.time() + 1.5
        while time.time() < deadline and got is None:
            msg = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=0.5)
            if msg and msg.param_id.rstrip("\x00") == name:
                got = (msg.param_value, msg.param_index, msg.param_count)
        if got:
            break
    print(f"{name} = {got}", flush=True)
