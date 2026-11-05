"""SERVO5 for the Pi-driven camera tilt, through the router's GCS port.

    PYTHONPATH=pylib python3 servo5_check.py [--set-function-0]

Reads SERVO5_FUNCTION (and sets it to 0 with --set-function-0), then sends
MAV_CMD_DO_SET_SERVO on output 5 at the uncalibrated Camera cal pulses
(forward 1500, 45 down 1250, straight down 1000 us) and reads SERVO_OUTPUT_RAW
back after each. Refuses unless the FC heartbeat says disarmed. Moves only
output 5.
"""
import sys
import time

from pymavlink import mavutil

ROUTER = "udpout:127.0.0.1:14550"
POSES = (("FORWARD", 1500), ("ALIGN", 1250), ("NADIR", 1000), ("FORWARD", 1500))

m = mavutil.mavlink_connection(ROUTER, source_system=250, source_component=191, dialect="ardupilotmega")
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
target = (1, 1)
print("FC heartbeat: disarmed", flush=True)


def param(name, value=None):
    """Read (or set, then read) one parameter; returns its value."""
    for attempt in range(5):
        if value is None:
            m.mav.param_request_read_send(*target, name.encode(), -1)
        else:
            m.mav.param_set_send(*target, name.encode(), float(value),
                                 mavutil.mavlink.MAV_PARAM_TYPE_INT16)
        deadline = time.time() + 2
        while time.time() < deadline:
            msg = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=0.5)
            if msg and msg.param_id.rstrip("\x00") == name:
                return msg.param_value
    sys.exit(f"no PARAM_VALUE for {name}")


def servo5():
    """SERVO_OUTPUT_RAW servo5_raw, fresh: requested, then the next one."""
    m.mav.command_long_send(*target, mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE, 0,
                            36, 0, 0, 0, 0, 0, 0)
    deadline = time.time() + 2
    while time.time() < deadline:
        msg = m.recv_match(type="SERVO_OUTPUT_RAW", blocking=True, timeout=0.5)
        if msg and msg.port == 0:
            return msg.servo5_raw
    return None


print("SERVO5_FUNCTION =", int(param("SERVO5_FUNCTION")), flush=True)
if "--set-function-0" in sys.argv:
    print("SERVO5_FUNCTION set ->", int(param("SERVO5_FUNCTION", 0)), flush=True)
for name in ("SERVO5_MIN", "SERVO5_MAX", "SERVO5_TRIM", "BRD_SAFETY_MASK"):
    print(f"{name} = {param(name):g}", flush=True)
print("output 5 now:", servo5(), "us", flush=True)
for pose, pwm in POSES:
    m.mav.command_long_send(*target, mavutil.mavlink.MAV_CMD_DO_SET_SERVO, 0,
                            5, pwm, 0, 0, 0, 0, 0)
    ack = None
    deadline = time.time() + 3
    while time.time() < deadline and ack is None:
        msg = m.recv_match(type=["COMMAND_ACK", "STATUSTEXT"], blocking=True, timeout=0.5)
        if msg and msg.get_type() == "STATUSTEXT":
            print("   FC says:", msg.text, flush=True)
        elif msg and msg.command == mavutil.mavlink.MAV_CMD_DO_SET_SERVO:
            ack = msg.result
    time.sleep(1.0)
    print(f"{pose:8s} DO_SET_SERVO 5 {pwm} us: ack {ack} -> output 5 reads {servo5()} us", flush=True)
