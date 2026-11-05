"""RC_CHANNELS (65) on MAVROS's raw stream, grouped by sender (sysid, compid),
with the channel count and channels 1-8 each sender reports. 10 s, then exits.

    python3 /home/aerothon/state/deploy_20261025/rc_sources.py
"""
import struct
import time

import rclpy
from mavros_msgs.msg import Mavlink
from rclpy.qos import qos_profile_sensor_data

rclpy.init()
node = rclpy.create_node('rc_sources')
senders = {}


def on_msg(m):
    if m.msgid != 65:
        return
    raw = b''.join(struct.pack('<Q', w) for w in m.payload64)[:m.len].ljust(42, b'\0')
    t, *ch = struct.unpack_from('<I18H', raw)
    s = senders.setdefault((m.sysid, m.compid), {'n': 0, 'ch5': set()})
    s['n'] += 1
    s['ch5'].add(ch[4])
    s['last'] = (raw[40], raw[41], ch[:12])


node.create_subscription(Mavlink, '/uas1/mavlink_source', on_msg, qos_profile_sensor_data)
end = time.monotonic() + 10
while rclpy.ok() and time.monotonic() < end:
    rclpy.spin_once(node, timeout_sec=0.5)
for (sysid, compid), s in sorted(senders.items()):
    count, rssi, ch = s['last']
    print(f'sysid {sysid} compid {compid}: {s["n"]} msgs/10 s, chancount {count}, rssi {rssi}, '
          f'ch5 seen {sorted(s["ch5"])}, ch1-12 {ch}', flush=True)
print('senders', len(senders), flush=True)
