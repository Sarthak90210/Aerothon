"""Read-only after the reboot: the changed params, 12 s of traffic (are ELRS
overrides still forwarded here?), RC_CHANNELS and SYS_STATUS RC health."""
import collections
import time
from pymavlink import mavutil

m = mavutil.mavlink_connection("udpout:127.0.0.1:14550", source_system=250,
                               source_component=191, dialect="ardupilotmega")
m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
m.recv_match(type="HEARTBEAT", blocking=True, timeout=5)


def param(name):
    for _ in range(5):
        m.mav.param_request_read_send(1, 1, name.encode(), -1)
        end = time.time() + 2
        while time.time() < end:
            msg = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=0.5)
            if msg and msg.param_id.rstrip("\x00") == name:
                return msg.param_value


for n in ("SERIAL1_PROTOCOL", "SERIAL1_BAUD", "MAV2_OPTIONS", "MAV2_RC_CHAN", "BRD_SER2_RTSCTS",
          "SERIAL2_PROTOCOL", "SERIAL2_BAUD", "OSD_TYPE", "MSP_OPTIONS", "RSSI_TYPE"):
    print(f"{n} = {param(n):g}")
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
print("from other systems:", {k: v for k, v in seen.items() if k[0] != 1} or "none")
rc = last.get((1, 1, "RC_CHANNELS"))
if rc:
    print("RC_CHANNELS chancount", rc.chancount, "rssi", rc.rssi,
          "ch1-9", [getattr(rc, f"chan{i}_raw") for i in range(1, 10)])
ss = last.get((1, 1, "SYS_STATUS"))
if ss:
    RC = mavutil.mavlink.MAV_SYS_STATUS_SENSOR_RC_RECEIVER
    print("RC receiver present/enabled/healthy:", bool(ss.onboard_control_sensors_present & RC),
          bool(ss.onboard_control_sensors_enabled & RC), bool(ss.onboard_control_sensors_health & RC))
