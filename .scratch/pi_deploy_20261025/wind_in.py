"""Wind the L298N winch in for a bounded time through the running winch_ctrl,
by moving its channel-5 thresholds (switch left at LOW, ~1000 us):
  low 900 / high 1800  -> 1000 reads middle: hand drive ready, motor stopped
  high 950             -> 1000 reads HIGH: drive +1 = IN1 param (BCM23, IN3) = wind in
  high 1800            -> middle again: stop. rc_timeout_s 2.0 during the burst
(RC_CHANNELS ~4.5 Hz went stale at 0.5 s and dropped hand drive), then 0.5. Low stays 900 so LOW cannot lower.
The stop runs in finally, also on Ctrl-C or a lost SSH session.

    python3 /home/aerothon/state/deploy_20261025/wind_in.py 20
"""
import json
import sys
import time

import rclpy
from rcl_interfaces.srv import SetParameters
from rclpy.parameter import Parameter
from std_msgs.msg import String

secs = min(float(sys.argv[1]), 30.0)
rclpy.init()
node = rclpy.create_node('wind_in')
cli = node.create_client(SetParameters, '/winch_ctrl/set_parameters')
status = {}


def on_status(msg):
    d = json.loads(msg.data)
    key = (d.get('state'), d.get('rc_manual'), d.get('rc_manual_ready'))
    if key != status.get('key'):
        status['key'] = key
    if d.get('rc_manual') == 1:
        status['driving'] = status.get('driving', 0) + 1
        print(time.strftime('%H:%M:%S'), f'winch state {key[0]}, rc_manual {key[1]}, ready {key[2]}, '
              f'estimate {d.get("payout_estimate_m")} m', flush=True)


def spin(t):
    end = time.monotonic() + t
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.05)


def setp(**kw):
    req = SetParameters.Request(parameters=[Parameter(k, value=v).to_parameter_msg() for k, v in kw.items()])
    fut = cli.call_async(req)
    rclpy.spin_until_future_complete(node, fut, timeout_sec=5.0)
    ok = fut.result() is not None and all(r.successful for r in fut.result().results)
    print(time.strftime('%H:%M:%S'), 'set', kw, 'ok' if ok else 'FAILED', flush=True)
    return ok


node.create_subscription(String, '/winch/status', on_status, 10)
assert cli.wait_for_service(timeout_sec=10.0), 'winch_ctrl parameter service not available'
try:
    if setp(rc_low_us=900, rc_high_us=1800, rc_timeout_s=2.0):
        spin(0.8)                        # at least one 5 Hz tick sees the middle
        if setp(rc_high_us=950):
            print(time.strftime('%H:%M:%S'), f'WINDING IN for {secs:.0f} s', flush=True)
            spin(secs)
finally:
    for _ in range(3):
        if setp(rc_high_us=1800):
            break
    spin(1.0)
    setp(rc_timeout_s=0.5)
    print(time.strftime('%H:%M:%S'), f"STOP sent; driving in {status.get('driving', 0)} of the 5 Hz status samples; "
          'low stays parked at 900', flush=True)
