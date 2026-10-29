"""Read-only: named FC parameters over a link (default COM25), printed beside the restore file's value."""
import sys, time
from pymavlink import mavutil
link = sys.argv[1]
names = sys.argv[2:]
want = {}
for line in open("fc_restore_20261029.param"):
    if line[0] != "#" and "," in line:
        k, v = line.strip().split(",")
        want[k] = float(v)
if "," in link:
    port, baud = link.split(",")
    m = mavutil.mavlink_connection(port, baud=int(baud), source_system=250, source_component=191, dialect="ardupilotmega")
else:
    m = mavutil.mavlink_connection(link, source_system=250, source_component=191, dialect="ardupilotmega")
m.wait_heartbeat(timeout=10)
for n in names:
    got = None
    for _ in range(3):
        m.mav.param_request_read_send(1, 1, n.encode(), -1)
        end = time.time() + 1.5
        while time.time() < end and got is None:
            msg = m.recv_match(type="PARAM_VALUE", blocking=True, timeout=0.5)
            if msg and msg.param_id.rstrip("\x00") == n:
                got = msg.param_value
        if got is not None:
            break
    print(f"{n:18s} FC {got}  file {want.get(n)}")
