"""Inside the runtime: send camera poses through camera_ctrl (/camera/set_pose)
and sample FC output 5 (/mavros/rc/out, SERVO_OUTPUT_RAW) for 3 s after each,
so a pulse the FC takes back shows as a spread. Moves only the camera servo.
Ends at FORWARD."""
import json
import time

import rclpy
from mavros_msgs.msg import RCOut
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String

rclpy.init()
n = rclpy.create_node("servo5_hold_check")
pub = n.create_publisher(String, "/camera/set_pose", 10)
out, state = [], {}
n.create_subscription(RCOut, "/mavros/rc/out", lambda m: out.append(
    (time.monotonic(), m.channels[4] if len(m.channels) > 4 else None)), qos_profile_sensor_data)
n.create_subscription(String, "/camera/pose_state", lambda m: state.update(json.loads(m.data)), 10)


def spin(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        rclpy.spin_once(n, timeout_sec=0.05)


spin(2.0)
print("before: output 5", out[-1][1] if out else None, "| pose_state",
      {k: state.get(k) for k in ("pose", "output", "output_unit", "calibrated")}, flush=True)
for pose in ("FORWARD", "ALIGN", "NADIR", "FORWARD"):
    pub.publish(String(data=pose))
    spin(1.5)                                   # settle
    t = time.monotonic()
    spin(3.0)
    held = [v for ts, v in out if ts >= t and v is not None]
    print(f"{pose:8s} camera_ctrl output {state.get('output')} {state.get('output_unit')} | "
          f"FC output 5 over 3 s: {min(held) if held else None}..{max(held) if held else None} "
          f"({len(held)} samples)", flush=True)
