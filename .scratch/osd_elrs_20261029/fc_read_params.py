"""Read-only: the FC's whole parameter list through the router's GCS port,
saved to fc_params_<stamp>.json, with the serial/OSD/MSP/RC/RSSI ones printed.

    MAVLINK20=1 MAVLINK_DIALECT=ardupilotmega PYTHONPATH=pylib python3 fc_read_params.py OUT.json
"""
import json
import re
import sys
import time

from pymavlink import mavutil

out = sys.argv[1]
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
armed = bool(hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
print("FC heartbeat:", "ARMED" if armed else "disarmed", flush=True)

m.mav.command_long_send(1, 1, mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE, 0, 148, 0, 0, 0, 0, 0, 0)
ver = m.recv_match(type="AUTOPILOT_VERSION", blocking=True, timeout=3)
if ver:
    v = ver.flight_sw_version
    print(f"firmware {v >> 24 & 255}.{v >> 16 & 255}.{v >> 8 & 255} type {v & 255}, board {ver.board_version}", flush=True)
for _ in range(10):
    t = m.recv_match(type="STATUSTEXT", blocking=True, timeout=0.3)
    if t:
        print("  FC:", t.text)

params, total = {}, None
m.mav.param_request_list_send(1, 1)
last = time.time()
while time.time() - last < 4:
    msg = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=1)
    if not msg:
        continue
    last = time.time()
    total = msg.param_count
    params[msg.param_id.rstrip("\x00")] = (msg.param_index, msg.param_value)
    if total and len(params) >= total:
        break
# Fill gaps one by one.
if total:
    have = {i for i, _ in params.values()}
    for i in sorted(set(range(total)) - have):
        for _ in range(3):
            m.mav.param_request_read_send(1, 1, b"", i)
            msg = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=1)
            if msg and msg.param_index == i:
                params[msg.param_id.rstrip("\x00")] = (i, msg.param_value)
                break
print(f"{len(params)} of {total} parameters", flush=True)
json.dump({k: v for k, (i, v) in sorted(params.items())}, open(out, "w"), indent=0)
pat = re.compile(r"^(SERIAL\d_|OSD_TYPE|OSD1_ENABLE|OSD_OPTIONS|MSP_|RSSI_|RC_PROTOCOLS|RC_OPTIONS|"
                 r"RC_OVERRIDE|SYSID_MYGCS|MAV_GCS_SYSID|FS_THR_|FS_GCS|RC\d+_OPTION|FLTMODE_CH|"
                 r"BRD_SER|BRD_ALT|SERIAL_PASS|OSD_FONT|OSD_UNITS|TELEM_DELAY|MAV_OPTIONS)")
for k in sorted(params):
    if pat.match(k):
        print(f"{k} = {params[k][1]:g}")
