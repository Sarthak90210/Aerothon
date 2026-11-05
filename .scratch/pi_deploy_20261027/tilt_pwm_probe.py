"""Send each Camera cal pose and read SERVO5's PWM back from the FC (SERVO_OUTPUT_RAW).

    python3 /home/aerothon/state/deploy_20261027/tilt_pwm_probe.py
Refuses unless the FCU is connected and disarmed. Moves only the camera tilt.
"""
import sys
import time

import rclpy
from mavros_msgs.msg import RCOut, State
from std_msgs.msg import String

rclpy.init()
node = rclpy.create_node('tilt_pwm_probe')
seen = {}
node.create_subscription(State, '/mavros/state', lambda m: seen.update(armed=m.armed, connected=m.connected), 10)
node.create_subscription(RCOut, '/mavros/rc/out', lambda m: seen.update(out=list(m.channels), out_t=time.monotonic()), 10)
pub = node.create_publisher(String, '/camera/set_pose', 10)


def spin(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.05)


spin(3.0)
if seen.get('connected') is not True or seen.get('armed') is not False:
    sys.exit(f'refusing: FCU {seen.get("connected")}, armed {seen.get("armed")}')
if 'out' not in seen:
    sys.exit('no /mavros/rc/out (SERVO_OUTPUT_RAW) from the FC')
print('before: SERVO5', seen['out'][4], 'us', flush=True)
for pose in ('FORWARD', 'ALIGN', 'NADIR', 'FORWARD'):
    pub.publish(String(data=pose))
    spin(2.5)
    print(f'{pose:8s} -> SERVO5 {seen["out"][4]} us', flush=True)
