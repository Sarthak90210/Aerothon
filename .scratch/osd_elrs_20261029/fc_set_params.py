"""Set FC parameters through the router's GCS port and read each back.

    MAVLINK20=1 MAVLINK_DIALECT=ardupilotmega PYTHONPATH=pylib python3 fc_set_params.py NAME=VALUE ...

Refuses unless the FC heartbeat says disarmed. Prints before -> after.
"""
import sys
import time

from pymavlink import mavutil

pairs = [a.split("=", 1) for a in sys.argv[1:]]
m = mavutil.mavlink_connection("udpout:127.0.0.1:14550", source_system=250,
                               source_component=191, dialect="ardupilotmega")
hb = None
end = time.time() + 15
while time.time() < end and hb is None:
    m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
    msg = m.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
    if msg and msg.get_srcSystem() == 1 and msg.get_srcComponent() == 1:
        hb = msg
if hb is None:
    sys.exit("no FC heartbeat through the router")
if hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED:
    sys.exit("refusing: the FC reports ARMED")
print("FC heartbeat: disarmed", flush=True)


def param(name, value=None):
    for _ in range(5):
        if value is None:
            m.mav.param_request_read_send(1, 1, name.encode(), -1)
        else:
            m.mav.param_set_send(1, 1, name.encode(), float(value), mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
        deadline = time.time() + 2
        while time.time() < deadline:
            msg = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=0.5)
            if msg and msg.param_id.rstrip("\x00") == name:
                return msg.param_value
    sys.exit(f"no PARAM_VALUE for {name}")


bad = 0
for name, value in pairs:
    before = param(name)
    after = param(name, float(value))
    ok = abs(after - float(value)) < 1e-6
    bad += not ok
    print(f"{name}: {before:g} -> {after:g}{'' if ok else '  NOT ACCEPTED'}", flush=True)
sys.exit(1 if bad else 0)
