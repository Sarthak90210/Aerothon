"""Read-only: does the FC answer what the Pi sends? Requests AUTOPILOT_VERSION
and one parameter by index over MAVLink 2 and MAVLink 1, prints any reply.

    MAVLINK_DIALECT=ardupilotmega PYTHONPATH=pylib python3 fc_uplink_check.py
"""
import os
import time

for version in ("2", "1"):
    os.environ["MAVLINK20"] = "1" if version == "2" else ""
    from importlib import reload
    from pymavlink import mavutil
    reload(mavutil)
    m = mavutil.mavlink_connection("udpout:127.0.0.1:14550", source_system=255,
                                   source_component=190, dialect="ardupilotmega")
    if version == "1":
        m.mav.WIRE_PROTOCOL_VERSION = "1.0"
    got = {}
    end = time.time() + 6
    while time.time() < end:
        m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
        m.mav.command_long_send(1, 1, mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE, 0, 148, 0, 0, 0, 0, 0, 0)
        m.mav.param_request_read_send(1, 1, b"", 0)
        stop = time.time() + 1
        while time.time() < stop:
            msg = m.recv_match(blocking=True, timeout=0.3)
            if msg and msg.get_srcSystem() == 1 and msg.get_srcComponent() == 1:
                t = msg.get_type()
                got[t] = got.get(t, 0) + 1
                if t in ("COMMAND_ACK", "PARAM_VALUE", "AUTOPILOT_VERSION") and got[t] == 1:
                    print(f"  v{version} reply {t}: {msg.to_dict()}"[:300], flush=True)
    print(f"MAVLink {version} out: FC messages back {got}", flush=True)
    m.close()
