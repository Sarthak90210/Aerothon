"""Arrival rate and gaps of the transmitter channels on the Pi, 20 s:
/aerothon/rc/in (RC bridge), RC_CHANNELS on MAVROS's raw stream, and
/winch/status. Prints count, mean rate, median and longest gap, and how many
gaps exceed the winch's 0.5 s staleness limit.

    python3 /home/aerothon/state/deploy_20261025/rc_rate.py
"""
import statistics
import time

import rclpy
from mavros_msgs.msg import Mavlink, RCIn
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String

rclpy.init()
node = rclpy.create_node('rc_rate')
arrivals = {'/aerothon/rc/in': [], 'RC_CHANNELS raw': [], '/winch/status': []}
node.create_subscription(RCIn, '/aerothon/rc/in',
                         lambda m: arrivals['/aerothon/rc/in'].append(time.monotonic()), qos_profile_sensor_data)
node.create_subscription(Mavlink, '/uas1/mavlink_source',
                         lambda m: m.msgid == 65 and arrivals['RC_CHANNELS raw'].append(time.monotonic()),
                         qos_profile_sensor_data)
node.create_subscription(String, '/winch/status',
                         lambda m: arrivals['/winch/status'].append(time.monotonic()), 10)
end = time.monotonic() + 20
while rclpy.ok() and time.monotonic() < end:
    rclpy.spin_once(node, timeout_sec=0.05)
for name, t in arrivals.items():
    if len(t) < 2:
        print(f'{name}: {len(t)} messages', flush=True)
        continue
    gaps = [b - a for a, b in zip(t, t[1:])]
    print(f'{name}: {len(t)} msgs, {len(t) / (t[-1] - t[0]):.1f} Hz, median gap {statistics.median(gaps):.3f} s, '
          f'longest {max(gaps):.3f} s, gaps > 0.5 s: {sum(g > 0.5 for g in gaps)}', flush=True)
