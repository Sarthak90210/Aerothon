"""Decode RC_CHANNELS (65) and RC_CHANNELS_RAW (35) straight from MAVROS's raw
FCU stream, to see the channel count the FC actually reports."""
import struct
import time

import rclpy
from mavros_msgs.msg import Mavlink
from rclpy.qos import qos_profile_sensor_data

rclpy.init()
node = rclpy.create_node('rc_raw')
shown = {65: 0, 35: 0}


def on_msg(m):
    if m.msgid not in shown or shown[m.msgid] >= 3:
        return
    raw = b''.join(struct.pack('<Q', w) for w in m.payload64)[:m.len]
    raw = raw.ljust(42, b'\0')                     # MAVLink 2 trims trailing zeros
    if m.msgid == 65:
        t, *ch = struct.unpack_from('<I18H', raw)
        count, rssi = raw[40], raw[41]
        print(f'RC_CHANNELS chancount={count} rssi={rssi} ch1-8={ch[:8]}', flush=True)
    else:
        t, *rest = struct.unpack_from('<I8HBB', raw.ljust(22, b'\0'))
        print(f'RC_CHANNELS_RAW port={rest[8]} rssi={rest[9]} ch1-8={tuple(rest[:8])}', flush=True)
    shown[m.msgid] += 1


node.create_subscription(Mavlink, '/uas1/mavlink_source', on_msg, qos_profile_sensor_data)
end = time.monotonic() + 15
while rclpy.ok() and time.monotonic() < end and min(shown.values()) < 3:
    rclpy.spin_once(node, timeout_sec=0.5)
print('seen', shown, flush=True)
