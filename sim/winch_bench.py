#!/usr/bin/env python3
"""Winch bench in Gazebo: the airframe held at the drop height, one drop, filmed.

    python3 sim/winch_bench.py                   # 5 m, rulebook payload
    python3 sim/winch_bench.py --alt 5.5 --out /tmp/wb

The team airframe is welded to the world at --alt (no flight controller:
this isolates the winch), the rulebook's 10 x 5 x 5 cm, 100 g payload hangs
on the hook, and the REAL winch_ctrl (backend:=gazebo, gravity hook) runs
lower -> release -> stow while three cameras record:

    close   at the touchdown point, low, looking at the payload landing
    wide    from the side, the whole drop from the airframe to the ground
    nadir   the drone's own C270, tilted straight down: what the mission sees

The line is drawn onto the close and wide views from the winch joint's
position in Gazebo (the sim's line is a rigid prismatic joint with no
visual). Each frame is captioned with sim time, the winch state, the line
paid out, whether the hook has let go and the payload's height; the videos
run at sim-time speed, the three in step. Outputs in --out: drop.mp4 (the
three side by side), close.mp4, wide.mp4, nadir.mp4, events.txt and
timeline.csv.

WHAT THIS DOES AND DOES NOT SHOW. The sim's hook is a point on a prismatic
joint with a DetachableJoint to the payload. winch_ctrl opens it when it sees
the line go slack (line paying out, payload no longer following it): that is
the sequence and the trigger logic of a gravity hook, not the mechanics of
the team's hook. Whether the real hook lets go on touchdown is a bench test
with the real hook (docs/FIELD_READINESS.md, bench check 6). The rigid line
also carries on past the ground after the release, where a real one would
lie slack.
"""

import argparse
import csv
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = "aerothon_iris_c1_webcam"
VEHICLE = "aerothon_quad"
W, H, FPS = 960, 540, 20
VIEWS = ("close", "wide", "nadir")


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


# --------------------------------------------------------------------------- #
# The rig
# --------------------------------------------------------------------------- #
HOOK_VISUAL = """<visual name="bench_hook">
  <geometry><box><size>0.012 0.012 0.07</size></box></geometry><pose>0 0 0.035 0 0 0</pose>
  <material><ambient>1 0.45 0 1</ambient><diffuse>1 0.5 0.05 1</diffuse></material></visual>"""
HOOK_CURL = """<visual name="bench_hook_curl">
  <geometry><box><size>0.045 0.012 0.012</size></box></geometry><pose>0.017 0 0 0 0 0</pose>
  <material><ambient>1 0.45 0 1</ambient><diffuse>1 0.5 0.05 1</diffuse></material></visual>"""


def build_vehicle(out):
    """The team airframe, welded to the world, no ArduPilot, no lidar."""
    prefix = sh("ros2 pkg prefix ardupilot_gazebo")
    if not prefix:
        sys.exit("ardupilot_gazebo not found: source ~/aerothon_stack/install/setup.bash")
    models = out / "models"
    subprocess.run([sys.executable, str(ROOT / "scripts/materialize_vehicle_model.py"),
                    "--source", f"{prefix}/share/ardupilot_gazebo/models/iris_with_gimbal/model.sdf",
                    "--output-root", str(models), "--airframe", "cad"], check=True)
    path = models / MODEL / "model.sdf"
    tree = ET.parse(path)
    model = tree.getroot().find("model")
    for plugin in model.findall("plugin"):
        if "ArduPilot" in plugin.get("filename", ""):
            model.remove(plugin)            # lock-step would hold physics for SITL
    for link in model.findall("link"):
        for sensor in link.findall("sensor"):
            if sensor.get("type") == "gpu_lidar":
                link.remove(sensor)         # rendering it costs, nothing reads it
        if link.get("name") == "winch_hook":
            # The sim hook is a 12 mm grey sphere; film something visible.
            link.append(ET.fromstring(HOOK_VISUAL))
            link.append(ET.fromstring(HOOK_CURL))
    rig = ET.SubElement(model, "joint", name="bench_rig", type="fixed")
    ET.SubElement(rig, "parent").text = "world"
    ET.SubElement(rig, "child").text = "base_link"
    tree.write(path, encoding="utf-8", xml_declaration=True)
    airframe = json.loads((ROOT / "src/aerothon_sim/sim_gazebo/models/aerothon_quad/"
                           "airframe.json").read_text())
    return models, f"{prefix}/share/ardupilot_gazebo/models", airframe


class Cam:
    """A static pinhole camera: its SDF pose, and world points to pixels."""

    def __init__(self, eye, target, hfov):
        self.eye, self.hfov = eye, hfov
        dx, dy, dz = (t - e for t, e in zip(target, eye))
        self.yaw = math.atan2(dy, dx)
        self.pitch = -math.atan2(dz, math.hypot(dx, dy))    # +pitch looks down
        self.f = (W / 2.0) / math.tan(hfov / 2.0)

    def pose(self):
        e = self.eye
        return f"{e[0]} {e[1]} {e[2]} 0 {self.pitch:.4f} {self.yaw:.4f}"

    def project(self, p):
        dx, dy, dz = (a - b for a, b in zip(p, self.eye))
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        x1, y1 = cy * dx + sy * dy, -sy * dx + cy * dy
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        x, z = cp * x1 - sp * dz, sp * x1 + cp * dz
        if x <= 0.05:
            return None
        return (int(round(W / 2 - self.f * y1 / x)), int(round(H / 2 - self.f * z / x)))


def camera_model(name, cam):
    return f"""
    <model name="cam_{name}"><static>true</static>
      <pose>{cam.pose()}</pose>
      <link name="link">
        <sensor name="{name}" type="camera">
          <update_rate>{FPS}</update_rate><always_on>1</always_on>
          <topic>/bench/{name}</topic>
          <camera><horizontal_fov>{cam.hfov}</horizontal_fov>
            <image><width>{W}</width><height>{H}</height></image>
            <clip><near>0.02</near><far>60</far></clip></camera>
        </sensor>
      </link>
    </model>"""


def rig_geometry(alt, payload, airframe):
    hook_z = float(airframe["hook_z"])
    (dx, dy, _), _ = airframe["drop_mechanism"]
    return {
        "xy": (dx, dy),
        "pulley_z": alt + hook_z + 0.015,     # the prismatic joint's top
        "hook_z0": alt + hook_z,              # the hook at zero payout
        # Hung just under the hook, as the mission world hangs its payload.
        "payload_z0": alt + hook_z - 0.015 - payload[2] / 2.0,
        "cams": {
            "close": Cam((dx + 0.85, dy - 0.6, 0.32), (dx, dy, 0.18), 1.0),
            "wide": Cam((dx + 6.5, dy - 3.8, alt / 2 + 0.4), (dx, dy, alt / 2 + 0.1), 1.3),
        },
    }


def write_world(out, alt, payload, geo):
    dx, dy = geo["xy"]
    px, py, pz = payload
    world = f"""<?xml version="1.0"?>
<sdf version="1.9">
  <world name="winch_bench">
    <physics name="1ms" type="ignored"><max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor></physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine></plugin>
    <scene><ambient>0.55 0.55 0.55 1</ambient><background>0.62 0.75 0.9 1</background>
      <grid>false</grid></scene>
    <light type="directional" name="sun"><cast_shadows>true</cast_shadows>
      <pose>0 0 20 0 0 0</pose><diffuse>0.9 0.9 0.85 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular><direction>-0.4 0.3 -0.9</direction></light>

    <model name="ground"><static>true</static><link name="link">
      <collision name="c"><geometry><plane><normal>0 0 1</normal><size>60 60</size></plane></geometry>
        <surface><friction><ode><mu>1.0</mu><mu2>1.0</mu2></ode></friction></surface></collision>
      <visual name="v"><geometry><plane><normal>0 0 1</normal><size>60 60</size></plane></geometry>
        <material><ambient>0.30 0.45 0.22 1</ambient><diffuse>0.33 0.5 0.25 1</diffuse></material></visual>
    </link></model>

    <!-- The target pad under the drop point: white, 1.2 m, a black cross. -->
    <model name="pad"><static>true</static><pose>{dx} {dy} 0.002 0 0 0</pose><link name="link">
      <visual name="w"><geometry><box><size>1.2 1.2 0.004</size></box></geometry>
        <material><ambient>0.9 0.9 0.9 1</ambient><diffuse>0.95 0.95 0.95 1</diffuse></material></visual>
      <visual name="x"><pose>0 0 0.003 0 0 0</pose><geometry><box><size>0.6 0.04 0.002</size></box></geometry>
        <material><ambient>0.05 0.05 0.05 1</ambient><diffuse>0.05 0.05 0.05 1</diffuse></material></visual>
      <visual name="y"><pose>0 0 0.003 0 0 0</pose><geometry><box><size>0.04 0.6 0.002</size></box></geometry>
        <material><ambient>0.05 0.05 0.05 1</ambient><diffuse>0.05 0.05 0.05 1</diffuse></material></visual>
    </link></model>

    <!-- Rulebook Figure 1: 10 x 5 x 5 cm, 100 g, an eyelet on top. -->
    <model name="aerothon_payload"><pose>{dx} {dy} {geo["payload_z0"]:.4f} 0 0 0</pose>
      <link name="body">
        <inertial><mass>0.10</mass><inertia>
          <ixx>{0.1 * (py**2 + pz**2) / 12:.3e}</ixx><iyy>{0.1 * (px**2 + pz**2) / 12:.3e}</iyy>
          <izz>{0.1 * (px**2 + py**2) / 12:.3e}</izz><ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>
        <collision name="c"><geometry><box><size>{px} {py} {pz}</size></box></geometry>
          <surface><friction><ode><mu>1.0</mu><mu2>1.0</mu2></ode></friction></surface></collision>
        <visual name="v"><geometry><box><size>{px} {py} {pz}</size></box></geometry>
          <material><ambient>0.35 0.5 0.85 1</ambient><diffuse>0.45 0.6 0.95 1</diffuse></material></visual>
        <visual name="eyelet"><pose>0 0 {pz / 2 + 0.008} 1.5708 0 0</pose>
          <geometry><cylinder><radius>0.008</radius><length>0.004</length></cylinder></geometry>
          <material><ambient>0.6 0.6 0.65 1</ambient><diffuse>0.7 0.7 0.75 1</diffuse></material></visual>
      </link>
      <plugin filename="gz-sim-pose-publisher-system" name="gz::sim::systems::PosePublisher">
        <publish_link_pose>false</publish_link_pose><publish_model_pose>true</publish_model_pose>
        <publish_nested_model_pose>false</publish_nested_model_pose>
        <use_pose_vector_msg>false</use_pose_vector_msg><update_frequency>20</update_frequency>
      </plugin>
    </model>

    <include><uri>model://{MODEL}</uri><name>{VEHICLE}</name>
      <pose>0 0 {alt} 0 0 0</pose></include>
    {"".join(camera_model(n, c) for n, c in geo["cams"].items())}
  </world>
</sdf>
"""
    (out / "world.sdf").write_text(world)


def write_bridge(out):
    entries = [
        ("/clock", "/clock", "rosgraph_msgs/msg/Clock", "gz.msgs.Clock", "GZ_TO_ROS"),
        ("/winch/gz/payout", "/aerothon/winch/payout", "std_msgs/msg/Float64",
         "gz.msgs.Double", "ROS_TO_GZ"),
        ("/winch/gz/detach", "/aerothon/payload/detach", "std_msgs/msg/Empty",
         "gz.msgs.Empty", "ROS_TO_GZ"),
        ("/gimbal/direct_pitch", "/gimbal/direct_pitch", "std_msgs/msg/Float64",
         "gz.msgs.Double", "ROS_TO_GZ"),
        ("/sim/payload_pose", "/model/aerothon_payload/pose", "geometry_msgs/msg/Pose",
         "gz.msgs.Pose", "GZ_TO_ROS"),
        ("/bench/joints", f"/world/winch_bench/model/{VEHICLE}/joint_state",
         "sensor_msgs/msg/JointState", "gz.msgs.Model", "GZ_TO_ROS"),
        ("/bench/close", "/bench/close", "sensor_msgs/msg/Image", "gz.msgs.Image", "GZ_TO_ROS"),
        ("/bench/wide", "/bench/wide", "sensor_msgs/msg/Image", "gz.msgs.Image", "GZ_TO_ROS"),
        ("/bench/nadir", "/camera/image", "sensor_msgs/msg/Image", "gz.msgs.Image", "GZ_TO_ROS"),
    ]
    text = "".join(
        f"- ros_topic_name: \"{r}\"\n  gz_topic_name: \"{g}\"\n  ros_type_name: \"{rt}\"\n"
        f"  gz_type_name: \"{gt}\"\n  direction: {d}\n" for r, g, rt, gt, d in entries)
    (out / "bridge.yaml").write_text(text)


# --------------------------------------------------------------------------- #
# The drop, and the recording
# --------------------------------------------------------------------------- #
def run_drop(out, alt, geo, max_sim_s):
    import cv2
    import rclpy
    from cv_bridge import CvBridge
    from geometry_msgs.msg import Pose, PoseStamped, TwistStamped
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Image, JointState
    from std_msgs.msg import Float64, String

    rclpy.init()
    node = Node("winch_bench", parameter_overrides=[
        Parameter("use_sim_time", Parameter.Type.BOOL, True)])
    bridge = CvBridge()
    st = {"status": {}, "payload": None, "line": None, "phase": "hanging", "t_written": None}
    latest, writers, frames = {}, {}, {}
    events, rows = [], []
    dx, dy = geo["xy"]

    def now():
        return node.get_clock().now().nanoseconds * 1e-9

    def event(what):
        t = now()
        events.append((t, what))
        node.get_logger().info(f"[t={t:6.2f}] {what}")

    def on_status(m):
        s = json.loads(m.data)
        old = st["status"]
        if s.get("hook_open") and not old.get("hook_open"):
            event(f"HOOK LET GO (payload z {st['payload']:.3f} m, "
                  f"line out {s['payout_m']:.2f} m)")
        if s.get("state") != old.get("state"):
            event(f"winch {old.get('state', '-')} -> {s.get('state')}")
        st["status"] = s

    def on_payload(m):
        st["payload"] = m.position.z

    def on_joints(m):
        if "winch_joint" in m.name:
            st["line"] = m.position[m.name.index("winch_joint")]

    def on_image(view):
        def cb(m):
            try:
                img = bridge.imgmsg_to_cv2(m, desired_encoding="bgr8")
            except Exception:                           # noqa: BLE001
                return
            latest[view] = img if img.shape[1] == W else cv2.resize(img, (W, H))
        return cb

    def draw_line(img, view):
        cam = geo["cams"].get(view)
        if cam is None or st["line"] is None:
            return
        top = cam.project((dx, dy, geo["pulley_z"]))
        hook = cam.project((dx, dy, geo["hook_z0"] - st["line"]))
        if top and hook:
            cv2.line(img, top, hook, (40, 40, 40), 1, cv2.LINE_AA)
            cv2.circle(img, hook, 6, (0, 140, 255), 1, cv2.LINE_AA)

    def caption(img, view):
        s, pz = st["status"], st["payload"]
        lines = [f"{view}   t = {now():6.2f} s (sim)",
                 f"winch {s.get('state', '-')}   line out {s.get('payout_m', 0):.2f} m",
                 "hook OPEN - payload released" if s.get("hook_open") else "hook holding payload",
                 f"payload bottom {pz - 0.025:+.3f} m above ground" if pz is not None else "",
                 st["phase"]]
        for i, t in enumerate(lines):
            y = 26 + 24 * i
            cv2.putText(img, t, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 0, 0), 4,
                        cv2.LINE_AA)
            colour = (80, 230, 255) if i == 0 else (
                (60, 255, 60) if (i == 2 and s.get("hook_open")) else (255, 255, 255))
            cv2.putText(img, t, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.62, colour, 1,
                        cv2.LINE_AA)
        return img

    def write_frames():
        """One frame per view per 1/FPS of SIM time: the videos play at sim
        speed and stay in step, whatever rate the renderer managed."""
        t = now()
        if st["t_written"] is not None and t - st["t_written"] < 1.0 / FPS - 1e-3:
            return
        if not all(v in latest for v in VIEWS):
            return
        st["t_written"] = t
        for v in VIEWS:
            if v not in writers:
                writers[v] = cv2.VideoWriter(str(out / f"{v}.avi"),
                                             cv2.VideoWriter_fourcc(*"MJPG"), FPS, (W, H))
            img = latest[v].copy()
            draw_line(img, v)
            writers[v].write(caption(img, v))
            frames[v] = frames.get(v, 0) + 1

    node.create_subscription(String, "/winch/status", on_status, 10)
    node.create_subscription(Pose, "/sim/payload_pose", on_payload, qos_profile_sensor_data)
    node.create_subscription(JointState, "/bench/joints", on_joints, qos_profile_sensor_data)
    for view in VIEWS:
        node.create_subscription(Image, f"/bench/{view}", on_image(view),
                                 qos_profile_sensor_data)
    pub_pose = node.create_publisher(PoseStamped, "/mavros/local_position/pose", 10)
    pub_vel = node.create_publisher(TwistStamped, "/mavros/local_position/velocity_local", 10)
    pub_cmd = node.create_publisher(String, "/winch/cmd", 10)
    pub_tilt = node.create_publisher(Float64, "/gimbal/direct_pitch", 10)

    def tick():
        # The flight controller's view of the hovering aircraft: the winch
        # reads its altitude and speed from these.
        p = PoseStamped()
        p.header.stamp = node.get_clock().now().to_msg()
        p.pose.position.z = float(alt)
        p.pose.orientation.w = 1.0
        pub_pose.publish(p)
        v = TwistStamped()
        v.header.stamp = p.header.stamp
        pub_vel.publish(v)
        pub_tilt.publish(Float64(data=-math.pi / 2))    # C270 straight down
        write_frames()
        s, t = st["status"], now()
        rows.append((round(t, 3), s.get("state"), s.get("payout_m"), st["line"],
                     s.get("hook_open"), s.get("released"), st["payload"]))
        ph = st["phase"]
        if ph == "hanging" and t > 3.0 and s:
            pub_cmd.publish(String(data="lower"))
            st["phase"] = "lowering: the motor pays out line"
            event("command: lower")
        elif ph.startswith("lowering") and s.get("state") == "AT_GROUND":
            pub_cmd.publish(String(data="release"))
            st["phase"] = "down: release recorded"
            st["t_down"] = t
            event("command: release (a gravity hook: bookkeeping only)")
        elif ph.startswith("down") and t - st["t_down"] > 2.0:
            pub_cmd.publish(String(data="stow"))
            st["phase"] = "stowing: the motor winds the hook back up"
            event("command: stow")
        elif ph.startswith("stowing") and s.get("payout_m", 1) <= 1e-3:
            st["phase"] = "stowed: the payload stayed on the ground"
            st["t_done"] = t
            event("hook stowed")
        elif ph.startswith("stowed") and t - st["t_done"] > 3.0:
            st["phase"] = "done"

    node.create_timer(1.0 / FPS, tick)
    wall0 = time.time()
    while rclpy.ok() and st["phase"] != "done":
        rclpy.spin_once(node, timeout_sec=0.1)
        if now() > max_sim_s or time.time() - wall0 > 60 * 30:
            event("timed out")
            break
    for w in writers.values():
        w.release()
    with open(out / "timeline.csv", "w", newline="") as f:
        cw = csv.writer(f)
        cw.writerow(["sim_t", "winch_state", "payout_m", "joint_m", "hook_open",
                     "released", "payload_z"])
        cw.writerows(rows)
    (out / "events.txt").write_text("".join(f"{t:7.2f}  {w}\n" for t, w in events))
    node.destroy_node()
    rclpy.shutdown()
    return frames


def encode(out):
    for v in VIEWS:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out / f"{v}.avi"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22",
                        str(out / f"{v}.mp4")], check=True)
        (out / f"{v}.avi").unlink()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    *sum((["-i", str(out / f"{v}.mp4")] for v in VIEWS), []),
                    "-filter_complex", "[0:v][1:v][2:v]hstack=inputs=3", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-crf", "23", str(out / "drop.mp4")], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--alt", type=float, default=5.0, help="airframe height, m")
    ap.add_argument("--payload", type=float, nargs=3, default=(0.10, 0.05, 0.05),
                    metavar=("X", "Y", "Z"), help="payload box, m (rulebook Fig. 1)")
    ap.add_argument("--out", type=Path, default=ROOT / "logs" / "winch_bench")
    ap.add_argument("--max-sim-s", type=float, default=90.0)
    args = ap.parse_args()

    out = args.out.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    models, upstream, airframe = build_vehicle(out)
    geo = rig_geometry(args.alt, args.payload, airframe)
    write_world(out, args.alt, args.payload, geo)
    write_bridge(out)

    env = dict(os.environ,
               GZ_SIM_RESOURCE_PATH=os.pathsep.join(
                   [str(models), upstream, os.environ.get("GZ_SIM_RESOURCE_PATH", "")]),
               GZ_PARTITION=f"winch_bench_{os.getpid()}", GZ_IP="127.0.0.1",
               ROS_DOMAIN_ID=os.environ.get("ROS_DOMAIN_ID", "61"), ROS_LOCALHOST_ONLY="1")
    os.environ.update({k: env[k] for k in ("GZ_PARTITION", "GZ_IP", "ROS_DOMAIN_ID",
                                           "ROS_LOCALHOST_ONLY")})
    procs = []

    def start(cmd, log):
        procs.append(subprocess.Popen(cmd, env=env, stdout=open(out / log, "w"),
                                      stderr=subprocess.STDOUT, start_new_session=True))

    try:
        start(["gz", "sim", "-s", "-r", "--headless-rendering", str(out / "world.sdf")],
              "gz.log")
        start(["ros2", "run", "ros_gz_bridge", "parameter_bridge", "--ros-args",
               "-p", f"config_file:={out / 'bridge.yaml'}"], "bridge.log")
        start([sys.executable, "-c", "from winch_ctrl.winch_node import main; main()",
               "--ros-args", "-p", "backend:=gazebo", "-p", "use_sim_time:=true"],
              "winch.log")
        frames = run_drop(out, args.alt, geo, args.max_sim_s)
    finally:
        for sig in (signal.SIGINT, signal.SIGKILL):
            for p in procs:
                try:
                    os.killpg(p.pid, sig)
                except ProcessLookupError:
                    pass
            time.sleep(2)

    print(f"frames: {frames}")
    encode(out)
    print((out / "events.txt").read_text())
    print(f"outputs in {out}")


if __name__ == "__main__":
    main()
