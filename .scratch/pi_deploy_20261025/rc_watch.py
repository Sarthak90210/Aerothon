"""Watch the FC's RC input (through the runtime's RC bridge) and the winch's hand-switch command; print only changes.

Runs inside the aerothon-runtime container (ROS domain 42); the hand
switch channel is the argument (default 6, the aircraft's RC6):
    python3 /home/aerothon/state/deploy_20261025/rc_watch.py [channel]
"""
import json
import sys
import time

import rclpy
from mavros_msgs.msg import RCIn
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String

rclpy.init()
node = rclpy.create_node('rc_watch')
CH = int(sys.argv[1]) if len(sys.argv) > 1 else 6
seen = {'count': None, 'ch': None, 'manual': None, 'last_rc': 0.0, 'quiet_said': False}


def say(text):
    print(time.strftime('%H:%M:%S ') + text, flush=True)


def on_rc(msg):
    ch = list(msg.channels)
    seen['last_rc'] = time.monotonic()
    seen['quiet_said'] = False
    if len(ch) != seen['count']:
        seen['count'] = len(ch)
        say(f'RC channels from FC: {len(ch)} {ch[:8]}')
    if len(ch) >= CH:
        v = ch[CH - 1]
        if seen['ch'] is None or abs(v - seen['ch']) > 40:
            seen['ch'] = v
            band = 'HIGH (>=1800, IN1/IN3)' if v >= 1800 else 'LOW (900-1200, IN2/IN4)' if 900 <= v <= 1200 else 'middle (stop)'
            say(f'ch{CH} = {v} us -> {band}')


def on_winch(msg):
    try:
        d = json.loads(msg.data)
    except ValueError:
        return
    m = (d.get('rc_manual'), d.get('rc_manual_ready'))
    if m != seen['manual']:
        seen['manual'] = m
        say(f"winch rc_manual = {m[0]}, ready {m[1]} (state {d.get('state')}, "
            f"payout {d.get('payout_m')} m, mission_active {d.get('mission_active')})")


node.create_subscription(RCIn, '/aerothon/rc/in', on_rc, qos_profile_sensor_data)
node.create_subscription(String, '/winch/status', on_winch, 10)
say(f'watching ch{CH} on /aerothon/rc/in (RC bridge) and /winch/status')
start = time.monotonic()
while rclpy.ok():
    rclpy.spin_once(node, timeout_sec=0.5)
    if time.monotonic() - max(seen['last_rc'], start) > 10 and not seen['quiet_said']:
        seen['quiet_said'] = True
        say('no /aerothon/rc/in message for 10 s')
