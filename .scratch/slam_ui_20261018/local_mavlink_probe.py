from collections import Counter
import json
import time
from pymavlink import mavutil

link = mavutil.mavlink_connection('tcp:127.0.0.1:5762', source_system=253)
counts, latest = Counter(), {}
end = time.monotonic()+8
while time.monotonic() < end:
    msg = link.recv_match(blocking=True, timeout=1)
    if msg:
        kind = msg.get_type()
        counts[kind] += 1
        if kind in ('LOCAL_POSITION_NED', 'HOME_POSITION', 'HEARTBEAT', 'EKF_STATUS_REPORT'):
            latest[kind] = msg.to_dict()
print(json.dumps({'counts': counts, 'latest': latest}, indent=2))
