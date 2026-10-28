"""Read-only, inside the runtime container: RC6/RC8, the winch's hand drive and
any /winch/cmd, one line per change, for the operator's switch test.

    python3 hand_drive_probe.py check        wait for the new winch status, 10 s of rates
    python3 hand_drive_probe.py record 600   log changes for 600 s (flushes each line)
"""
import json
import sys
import time

import rclpy
from mavros_msgs.msg import RCIn
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String

mode = sys.argv[1]
seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
rclpy.init()
n = rclpy.create_node("hand_drive_probe")
t0 = time.monotonic()
rc_t, last = [], {}
seen = {"winch": None, "mission": None, "cmd": []}


def out(text):
    print(f"{time.strftime('%H:%M:%S')}.{int(time.time() * 10) % 10} {text}", flush=True)


def on_rc(m):
    rc_t.append(time.monotonic())
    ch = list(m.channels)
    now = {"rc6": ch[5] if len(ch) > 5 else None, "rc8": ch[7] if len(ch) > 7 else None}
    if mode == "record" and any(abs((now[k] or 0) - (last.get(k) or 0)) > 10 for k in now):
        out(f"RC6 {now['rc6']} RC8 {now['rc8']}")
    if len(rc_t) > 1 and rc_t[-1] - rc_t[-2] > 0.4 and mode == "record":
        out(f"channels gap {rc_t[-1] - rc_t[-2]:.2f} s")
    last.update(now)


def on_winch(m):
    w = json.loads(m.data)
    key = (w.get("state"), w.get("rc_manual"), w.get("rc_manual_reason"), w.get("fault"))
    if mode == "record" and key != seen.get("key"):
        out(f"winch {w.get('state')} rc_manual {w.get('rc_manual')} ({w.get('rc_manual_reason')}) "
            f"payout {w.get('payout_estimate_m')} fault '{w.get('fault')}' RC6 {last.get('rc6')}")
    seen.update(winch=w, key=key)


def on_cmd(m):
    seen["cmd"].append(m.data)
    out(f"/winch/cmd {m.data}")


def on_mission(m):
    if mode == "record" and m.data != seen["mission"]:
        out(f"/mission/state {m.data}")
    seen["mission"] = m.data


n.create_subscription(RCIn, "/aerothon/rc/in", on_rc, qos_profile_sensor_data)
n.create_subscription(String, "/winch/status", on_winch, 10)
n.create_subscription(String, "/winch/cmd", on_cmd, 10)
n.create_subscription(String, "/mission/state", on_mission, 10)

if mode == "check":
    end = time.monotonic() + 90
    while time.monotonic() < end and not (seen["winch"] and "rc_manual_reason" in seen["winch"]):
        rclpy.spin_once(n, timeout_sec=0.2)
    w = seen["winch"] or {}
    print("winch status:", {k: w.get(k) for k in ("state", "rc_manual", "rc_manual_ready",
                                                   "rc_manual_reason", "payout_estimate_m", "fault")})
    rc_t.clear()
    end = time.monotonic() + 10
    while time.monotonic() < end:
        rclpy.spin_once(n, timeout_sec=0.05)
    gaps = [b - a for a, b in zip(rc_t, rc_t[1:])]
    print(f"/aerothon/rc/in {len(rc_t) / 10:.1f} Hz, worst gap {max(gaps) if gaps else float('nan'):.3f} s;",
          "RC6", last.get("rc6"), "RC8", last.get("rc8"))
else:
    out(f"recording {seconds:.0f} s")
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        rclpy.spin_once(n, timeout_sec=0.05)
    out("done")
