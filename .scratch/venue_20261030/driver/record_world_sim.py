"""Record a laptop-simulation (world maker) flight for independent grading.

Runtime domain 42: FCU pose/state (sim time), mission state, search pacing,
camera pose state and red-zone detail. Simulator domain 43: the payload's
TRUE pose (/sim/payload_pose), for grading only. Writes, into OUT_DIR:

    track.csv          sim/check_track.py's format (sim time, local ENU)
    pacing.jsonl       /mission/search_timing messages (+ wall time)
    camera.jsonl       /camera/pose_state messages (+ wall time)
    redzone.jsonl      /percep/redzone/detail status/reason (+ wall time)
    states.jsonl       mission state transitions

Stops once the aircraft has armed and then disarmed with the mission state
COMPLETED/FAILED/ABORTED, or after MAX_S wall seconds.
"""
import json
import os
import math
import sys
import time
from pathlib import Path

import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data, QoSProfile, QoSReliabilityPolicy
from geometry_msgs.msg import Pose, PoseStamped
from mavros_msgs.msg import State
from std_msgs.msg import String

out = Path(sys.argv[1])
max_s = float(sys.argv[2]) if len(sys.argv) > 2 else 5400
out.mkdir(parents=True, exist_ok=True)
logs = {k: open(out / f"{k}.jsonl", "a") for k in ("pacing", "camera", "redzone", "states")}

rt_ctx, sim_ctx = Context(), Context()
rclpy.init(context=rt_ctx, domain_id=42)
rclpy.init(context=sim_ctx, domain_id=43)
rt = rclpy.create_node("world_sim_recorder", context=rt_ctx,
                       parameter_overrides=[Parameter("use_sim_time", Parameter.Type.BOOL, True)])
sim = rclpy.create_node("world_sim_payload_truth", context=sim_ctx)
best = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.BEST_EFFORT)
st = {"state": State(), "mission": None, "payload": None, "armed_seen": False}
track = []


def log(kind, data):
    logs[kind].write(json.dumps({"wall": time.time(), **data}) + "\n")
    logs[kind].flush()


def on_pose(m):
    t = rt.get_clock().now().nanoseconds * 1e-9
    if t <= 0 or (track and t - track[-1][0] < 0.1):
        return
    p, q = m.pose.position, m.pose.orientation
    roll = math.degrees(math.atan2(2 * (q.w * q.x + q.y * q.z), 1 - 2 * (q.x * q.x + q.y * q.y)))
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, 2 * (q.w * q.y - q.z * q.x)))))
    track.append((t, p.x, p.y, p.z, bool(st["state"].armed), str(st["mission"]), roll, pitch,
                  str(st["state"].mode), st["payload"]))
    if st["state"].armed:
        st["armed_seen"] = True


def on_state(m):
    if m.data != st["mission"]:
        log("states", {"state": m.data, "t_sim": rt.get_clock().now().nanoseconds * 1e-9})
    st["mission"] = m.data


def as_json(kind, keep=None):
    def cb(m):
        try:
            d = json.loads(m.data)
        except ValueError:
            return
        log(kind, {k: d.get(k) for k in keep} if keep else d)
    return cb


rt.create_subscription(State, "/mavros/state", lambda m: st.__setitem__("state", m), best)
rt.create_subscription(PoseStamped, "/mavros/local_position/pose", on_pose, qos_profile_sensor_data)
rt.create_subscription(String, "/mission/state", on_state, 10)
rt.create_subscription(String, "/mission/search_timing", as_json("pacing"), 10)
rt.create_subscription(String, "/camera/pose_state", as_json("camera"), 10)
rt.create_subscription(String, "/percep/redzone/detail",
                       as_json("redzone", ("status", "reason", "blobs", "confirmed_area_m2")), 10)
sim.create_subscription(Pose, "/sim/payload_pose",
                        lambda m: st.__setitem__("payload", (m.position.x, m.position.y, m.position.z)), best)
ex_rt, ex_sim = SingleThreadedExecutor(context=rt_ctx), SingleThreadedExecutor(context=sim_ctx)
ex_rt.add_node(rt)
ex_sim.add_node(sim)


def write_track():
    with open(out / "track.csv", "w", encoding="utf-8") as f:
        f.write("t_sim,x,y,z,armed,state,roll_deg,pitch_deg,mode,payload_wx,payload_wy,payload_wz\n")
        for t, x, y, z, armed, s, r, pt, mode, pay in track:
            pw = ",".join(f"{v:.3f}" for v in pay) if pay else ",,"
            f.write(f"{t:.2f},{x:.3f},{y:.3f},{z:.3f},{int(armed)},{s},{r:.1f},{pt:.1f},{mode},{pw}\n")


t0, last_write = time.time(), 0.0
while time.time() - t0 < max_s:
    ex_rt.spin_once(timeout_sec=0.02)
    ex_sim.spin_once(timeout_sec=0.0)
    if time.time() - last_write > 30:
        write_track()
        last_write = time.time()
    # A testing-options campaign (UNTIL_KILLED=1) records until its session ends.
    done = os.environ.get("UNTIL_KILLED") != "1" and st["armed_seen"] and not st["state"].armed and str(st["mission"]).split(":")[0] in (
        "COMPLETED", "FAILED", "ABORTED")
    if done:
        for _ in range(50):                    # a few more samples after disarm
            ex_rt.spin_once(timeout_sec=0.02)
        break
write_track()
print(json.dumps({"samples": len(track), "armed_seen": st["armed_seen"], "final_state": st["mission"],
                  "payload_seen": st["payload"] is not None, "wall_s": round(time.time() - t0)}))
