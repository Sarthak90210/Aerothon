"""Read-only, 20 s inside the runtime: /aerothon/rc/in rate and worst gap
(winch_ctrl and camera_ctrl stop the hand drive past 0.5 s), RC6/RC8 values,
/mission/state and /winch/status."""
import json
import time
import rclpy
from rclpy.qos import qos_profile_sensor_data
from mavros_msgs.msg import RCIn
from std_msgs.msg import String

rclpy.init()
n = rclpy.create_node("rc_gap_probe")
stamps, last, seen = [], {}, {}
n.create_subscription(RCIn, "/aerothon/rc/in", lambda m: (stamps.append(time.monotonic()), last.update(ch=list(m.channels))), qos_profile_sensor_data)
n.create_subscription(String, "/mission/state", lambda m: seen.update(mission=m.data), 10)
n.create_subscription(String, "/winch/status", lambda m: seen.update(winch=m.data), 10)
end = time.monotonic() + 20
while time.monotonic() < end:
    rclpy.spin_once(n, timeout_sec=0.05)
gaps = [b - a for a, b in zip(stamps, stamps[1:])]
print(f"/aerothon/rc/in: {len(stamps)} msgs in 20 s, worst gap {max(gaps) if gaps else None:.3f} s, gaps > 0.5 s: {sum(g > 0.5 for g in gaps)}")
ch = last.get("ch", [])
print("RC6", ch[5] if len(ch) > 5 else None, "RC8", ch[7] if len(ch) > 7 else None)
print("mission state:", seen.get("mission"))
w = json.loads(seen["winch"]) if "winch" in seen else {}
print("winch:", {k: w.get(k) for k in ("state", "fault", "rc_manual", "rc_manual_ready", "payout_estimate_m", "limit", "backend")})
