"""Write a Mission Planner .param file to the FC, only what differs, each read back.

    MAVLINK20=1 MAVLINK_DIALECT=ardupilotmega PYTHONPATH=pylib \
        python3 fc_write_params.py FILE.param [udpout:127.0.0.1:14550 | COM5,115200]

Refuses unless the FC answers and its heartbeat says disarmed (checked again
every 100 writes). Downloads the whole list first; parameters the FC does not
have yet (they appear once their feature is enabled and the FC rebooted) are
listed as such, for a second pass after the reboot. Prints a summary line.
"""
import sys
import time

from pymavlink import mavutil

path = sys.argv[1]
link = sys.argv[2] if len(sys.argv) > 2 else "udpout:127.0.0.1:14550"
want = {}
for line in open(path, encoding="ascii"):
    line = line.strip()
    if line and not line.startswith("#"):
        name, value = line.replace("\t", ",").replace(" ", ",").split(",")[:2]
        want[name] = float(value)

if "," in link and not link.startswith("udp"):
    port, baud = link.split(",")
    m = mavutil.mavlink_connection(port, baud=int(baud), source_system=250,
                                   source_component=191, dialect="ardupilotmega")
else:
    m = mavutil.mavlink_connection(link, source_system=250, source_component=191,
                                   dialect="ardupilotmega")


def disarmed():
    end = time.time() + 10
    while time.time() < end:
        m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
        hb = m.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
        if hb and hb.get_srcSystem() == 1 and hb.get_srcComponent() == 1:
            return not hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
    sys.exit("no FC heartbeat")


if not disarmed():
    sys.exit("refusing: the FC reports ARMED")

have, total = {}, None
m.mav.param_request_list_send(1, 1)
last = time.time()
while time.time() - last < 5:
    msg = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=1)
    if msg:
        last, total = time.time(), msg.param_count
        have[msg.param_id.rstrip("\x00")] = (msg.param_index, msg.param_value, msg.param_type)
        if len(have) >= total:
            break
if not total:
    sys.exit("the FC answered no PARAM_REQUEST_LIST: it is not receiving this link")
for i in sorted(set(range(total)) - {v[0] for v in have.values()}):
    for _ in range(3):
        m.mav.param_request_read_send(1, 1, b"", i)
        msg = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=1)
        if msg and msg.param_index == i:
            have[msg.param_id.rstrip("\x00")] = (i, msg.param_value, msg.param_type)
            break
print(f"FC has {len(have)} of {total} parameters; file has {len(want)}", flush=True)

absent = sorted(k for k in want if k not in have)
todo = [(k, v) for k, v in sorted(want.items()) if k in have and abs(have[k][1] - v) > 1e-6 * max(1.0, abs(v))]
print(f"{len(todo)} differ, {len(want) - len(todo) - len(absent)} already equal, "
      f"{len(absent)} not on the FC yet", flush=True)
bad = []
for n, (name, value) in enumerate(todo):
    if n and n % 100 == 0 and not disarmed():
        sys.exit(f"stopped after {n} writes: the FC reports ARMED")
    after = None
    for _ in range(4):
        m.mav.param_set_send(1, 1, name.encode(), value, have[name][2])
        deadline = time.time() + 1.5
        while time.time() < deadline:
            msg = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=0.5)
            if msg and msg.param_id.rstrip("\x00") == name:
                after = msg.param_value
                break
        if after is not None and abs(after - value) <= 1e-6 * max(1.0, abs(value)):
            break
    ok = after is not None and abs(after - value) <= 1e-6 * max(1.0, abs(value))
    print(f"{name}: {have[name][1]:g} -> {after if after is None else f'{after:g}'}"
          f"{'' if ok else '  NOT ACCEPTED (wanted %g)' % value}", flush=True)
    if not ok:
        bad.append(name)
if absent:
    print("not on the FC yet (reboot, then run again):", " ".join(absent), flush=True)
print(f"SUMMARY written {len(todo) - len(bad)}, refused {len(bad)} {' '.join(bad)}, "
      f"absent {len(absent)}", flush=True)
sys.exit(1 if bad else 0)
