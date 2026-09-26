#!/usr/bin/env python3
"""Winch bench in Gazebo: the airframe held at the drop height, one drop, filmed.

    python3 sim/winch_bench.py                     # 5 m, the claw as drawn
    python3 sim/winch_bench.py --claw latch        # a claw that stays open
    python3 sim/winch_bench.py --alt 5.5 --out /tmp/wb

The team airframe is welded to the world at --alt (no flight controller: only
the winch is under test). Its dropping mechanism is the CAD's: the spool on
the motor's axle and the scissor claw on the line (sim_gazebo/claw.py). The
rulebook payload (10 x 5 x 5 cm, 100 g) hangs from the claw's jaws by an
eyelet. The REAL winch_ctrl (backend:=gazebo, gravity hook) runs
lower -> release -> stow, and four cameras record in step, at sim-time speed:

    claw        16 cm from the claw, side on, where it lands on the payload
    mechanism   the housing, spool and claw under the airframe
    wide        the whole drop from the side
    nadir       the drone's own C270 looking straight down: what the mission sees

THE CLAW. Gazebo cannot hold a closed linkage, so this bench plays the claw's
mechanics: while the payload hangs, the line is taut and the claw shut; once
the payload rests, line paid out beyond that is slack, the top pin comes down
toward the jaws and they open by the linkage's geometry; with the tips spread
past the eyelet's wire the payload is free. On the way back up:

    --claw as_drawn   the CAD has no latch: lifting the top pin pulls the
                      jaws shut again, as a hanging pair of tongs does. If
                      the eyelet is still between the tips, the claw closes
                      on it again and lifts the payload (straight up, with
                      the airframe welded in place, it always is).
    --claw latch      the jaws stay open until the claw is stowed

The captions set what winch_ctrl BELIEVES (it infers the release from slack)
against what the claw DID. Outputs in --out: drop.mp4 (the four views),
claw.mp4, mechanism.mp4, wide.mp4, nadir.mp4, claw_release_4x_slow.mp4,
events.txt and timeline.csv.
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
sys.path.insert(0, str(ROOT / "src/aerothon_sim/sim_gazebo"))
from sim_gazebo.claw import Claw                                  # noqa: E402

MODEL = "aerothon_iris_c1_webcam"
VEHICLE = "aerothon_quad"
W, H, FPS = 960, 540, 20
VIEWS = ("claw", "mechanism", "wide", "nadir")
EYELET_WIRE = 0.002          # eyelet wire diameter, m
EYELET_H = 0.010             # eyelet height above the payload's top, m
CLAW_TAU_S = 0.12            # the jaws swing open or shut, first order


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


# --------------------------------------------------------------------------- #
# The rig
# --------------------------------------------------------------------------- #
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
    if model.find("link[@name='claw_pivot']") is None:
        sys.exit("the vehicle has no claw: regenerate airframe.json with scripts/cad_to_gazebo.py")
    for plugin in model.findall("plugin"):
        if "ArduPilot" in plugin.get("filename", ""):
            model.remove(plugin)            # lock-step would hold physics for SITL
    for link in model.findall("link"):
        for sensor in link.findall("sensor"):
            if sensor.get("type") == "gpu_lidar":
                link.remove(sensor)         # rendering it costs, nothing reads it
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
        return f"{e[0]:.4f} {e[1]:.4f} {e[2]:.4f} 0 {self.pitch:.4f} {self.yaw:.4f}"

    def project(self, p):
        dx, dy, dz = (a - b for a, b in zip(p, self.eye))
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        x1, y1 = cy * dx + sy * dy, -sy * dx + cy * dy
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        x, z = cp * x1 - sp * dz, sp * x1 + cp * dz
        if x <= 0.005:
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
            <clip><near>0.005</near><far>60</far></clip></camera>
        </sensor>
      </link>
    </model>"""


def rig_geometry(alt, payload, claw):
    """Where everything is, in the world, with the airframe at `alt`."""
    top, ctr = claw["top_pin"], claw["centre_pin"]
    x, y = ctr[0], claw["jaw_y"]
    # The eyelet's wire rests on the jaws' curled tips.
    seat_z = alt + claw["jaw_tip_z"] + 0.5 * EYELET_WIRE + 0.0015
    ptop = seat_z - 0.5 * EYELET_WIRE - EYELET_H
    # Resting on the ground: the claw's centre pin this far up.
    rest_ctr = payload[2] + EYELET_H + 0.5 * EYELET_WIRE + (ctr[2] - seat_z + alt)
    return {
        "x": x, "y": y, "top": top, "exit": claw["line_exit"],
        "payload_z0": ptop - payload[2] / 2.0,
        "cams": {
            "claw": Cam((x, y - 0.16, rest_ctr + 0.004), (x, y, rest_ctr + 0.002), 0.45),
            "mechanism": Cam((x, y - 0.42, alt - 0.13), (x, y, alt - 0.14), 0.62),
            "wide": Cam((x + 6.5, y - 3.8, alt / 2 + 0.4), (x, y, alt / 2 + 0.1), 1.3),
        },
    }


def write_world(out, alt, payload, geo):
    x, y = geo["x"], geo["y"]
    px, py, pz = payload
    top = pz / 2 + EYELET_H
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
    <scene><ambient>0.6 0.6 0.6 1</ambient><background>0.62 0.75 0.9 1</background>
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
    <model name="pad"><static>true</static><pose>{x} {y} 0.002 0 0 0</pose><link name="link">
      <visual name="w"><geometry><box><size>1.2 1.2 0.004</size></box></geometry>
        <material><ambient>0.9 0.9 0.9 1</ambient><diffuse>0.95 0.95 0.95 1</diffuse></material></visual>
      <visual name="x"><pose>0 0 0.003 0 0 0</pose><geometry><box><size>0.6 0.04 0.002</size></box></geometry>
        <material><ambient>0.05 0.05 0.05 1</ambient><diffuse>0.05 0.05 0.05 1</diffuse></material></visual>
      <visual name="y"><pose>0 0 0.003 0 0 0</pose><geometry><box><size>0.04 0.6 0.002</size></box></geometry>
        <material><ambient>0.05 0.05 0.05 1</ambient><diffuse>0.05 0.05 0.05 1</diffuse></material></visual>
    </link></model>

    <!-- Rulebook Figure 1: 10 x 5 x 5 cm, 100 g, an eyelet on top. The eyelet
         is a wire staple whose top bar runs along y, across the jaws. -->
    <model name="aerothon_payload"><pose>{x} {y} {geo["payload_z0"]:.5f} 0 0 0</pose>
      <link name="body">
        <inertial><mass>0.10</mass><inertia>
          <ixx>{0.1 * (py**2 + pz**2) / 12:.3e}</ixx><iyy>{0.1 * (px**2 + pz**2) / 12:.3e}</iyy>
          <izz>{0.1 * (px**2 + py**2) / 12:.3e}</izz><ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia></inertial>
        <collision name="c"><geometry><box><size>{px} {py} {pz}</size></box></geometry>
          <surface><friction><ode><mu>1.0</mu><mu2>1.0</mu2></ode></friction></surface></collision>
        <visual name="v"><geometry><box><size>{px} {py} {pz}</size></box></geometry>
          <material><ambient>0.35 0.5 0.85 1</ambient><diffuse>0.45 0.6 0.95 1</diffuse></material></visual>
        <visual name="eyelet_bar"><pose>0 0 {top:.4f} 1.5708 0 0</pose>
          <geometry><cylinder><radius>{EYELET_WIRE / 2}</radius><length>0.014</length></cylinder></geometry>
          <material><ambient>0.75 0.75 0.8 1</ambient><diffuse>0.8 0.8 0.85 1</diffuse></material></visual>
        <visual name="eyelet_leg_l"><pose>0 0.006 {pz / 2 + EYELET_H / 2:.4f} 0 0 0</pose>
          <geometry><cylinder><radius>{EYELET_WIRE / 2}</radius><length>{EYELET_H}</length></cylinder></geometry>
          <material><ambient>0.75 0.75 0.8 1</ambient><diffuse>0.8 0.8 0.85 1</diffuse></material></visual>
        <visual name="eyelet_leg_r"><pose>0 -0.006 {pz / 2 + EYELET_H / 2:.4f} 0 0 0</pose>
          <geometry><cylinder><radius>{EYELET_WIRE / 2}</radius><length>{EYELET_H}</length></cylinder></geometry>
          <material><ambient>0.75 0.75 0.8 1</ambient><diffuse>0.8 0.8 0.85 1</diffuse></material></visual>
      </link>
      <plugin filename="gz-sim-pose-publisher-system" name="gz::sim::systems::PosePublisher">
        <publish_link_pose>false</publish_link_pose><publish_model_pose>true</publish_model_pose>
        <publish_nested_model_pose>false</publish_nested_model_pose>
        <use_pose_vector_msg>false</use_pose_vector_msg><update_frequency>50</update_frequency>
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
    to_gz = [("/bench/line", "/aerothon/winch/payout", "std_msgs/msg/Float64", "gz.msgs.Double"),
             ("/bench/spool", "/aerothon/winch/spool", "std_msgs/msg/Float64", "gz.msgs.Double"),
             ("/bench/detach", "/aerothon/payload/detach", "std_msgs/msg/Empty", "gz.msgs.Empty"),
             ("/bench/attach", "/aerothon/payload/attach", "std_msgs/msg/Empty", "gz.msgs.Empty"),
             ("/gimbal/direct_pitch", "/gimbal/direct_pitch", "std_msgs/msg/Float64",
              "gz.msgs.Double")]
    to_gz += [(f"/bench/claw/{j}", f"/aerothon/claw/{j}", "std_msgs/msg/Float64",
               "gz.msgs.Double") for j in ("link_a", "link_b", "pivot", "jaw_a", "jaw_b")]
    to_ros = [("/clock", "/clock", "rosgraph_msgs/msg/Clock", "gz.msgs.Clock"),
              ("/sim/payload_pose", "/model/aerothon_payload/pose", "geometry_msgs/msg/Pose",
               "gz.msgs.Pose"),
              ("/bench/joints", f"/world/winch_bench/model/{VEHICLE}/joint_state",
               "sensor_msgs/msg/JointState", "gz.msgs.Model"),
              ("/bench/nadir", "/camera/image", "sensor_msgs/msg/Image", "gz.msgs.Image")]
    to_ros += [(f"/bench/{v}", f"/bench/{v}", "sensor_msgs/msg/Image", "gz.msgs.Image")
               for v in VIEWS if v != "nadir"]
    text = "".join(
        f"- ros_topic_name: \"{r}\"\n  gz_topic_name: \"{g}\"\n  ros_type_name: \"{rt}\"\n"
        f"  gz_type_name: \"{gt}\"\n  direction: {d}\n"
        for entries, d in ((to_gz, "ROS_TO_GZ"), (to_ros, "GZ_TO_ROS"))
        for r, g, rt, gt in entries)
    (out / "bridge.yaml").write_text(text)


# --------------------------------------------------------------------------- #
# The claw's mechanics, the drop, and the recording
# --------------------------------------------------------------------------- #
def run_drop(out, alt, payload, geo, claw_geo, mode, max_sim_s):
    import cv2
    import rclpy
    from cv_bridge import CvBridge
    from geometry_msgs.msg import Pose, PoseStamped, TwistStamped
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Image, JointState
    from std_msgs.msg import Empty, Float64, String

    rclpy.init()
    node = Node("winch_bench", parameter_overrides=[
        Parameter("use_sim_time", Parameter.Type.BOOL, True)])
    bridge = CvBridge()
    claw = Claw(claw_geo)
    rest_z = payload[2] / 2.0
    st = {"status": {}, "payload": None, "q": {}, "payout": 0.0, "phase": "hanging",
          "t_written": None, "t_mech": None,
          # the claw
          "attached": True, "resting": False, "rest_line": None, "phi": 0.0,
          "claw_note": "shut, holding the eyelet", "regrabs": 0, "t_release": None}
    latest, writers, frames = {}, {}, {}
    events, rows = [], []

    def now():
        return node.get_clock().now().nanoseconds * 1e-9

    def event(what):
        t = now()
        events.append((t, what))
        node.get_logger().info(f"[t={t:6.2f}] {what}")

    pub = {k: node.create_publisher(Float64, f"/bench/claw/{k}", 10)
           for k in ("link_a", "link_b", "pivot", "jaw_a", "jaw_b")}
    pub_line = node.create_publisher(Float64, "/bench/line", 10)
    pub_spool = node.create_publisher(Float64, "/bench/spool", 10)
    pub_detach = node.create_publisher(Empty, "/bench/detach", 10)
    pub_attach = node.create_publisher(Empty, "/bench/attach", 10)
    pub_pose = node.create_publisher(PoseStamped, "/mavros/local_position/pose", 10)
    pub_vel = node.create_publisher(TwistStamped, "/mavros/local_position/velocity_local", 10)
    pub_cmd = node.create_publisher(String, "/winch/cmd", 10)
    pub_tilt = node.create_publisher(Float64, "/gimbal/direct_pitch", 10)

    def on_status(m):
        s = json.loads(m.data)
        old = st["status"]
        if s.get("hook_open") and not old.get("hook_open"):
            event("winch_ctrl infers the release (line slack)")
        if s.get("state") != old.get("state"):
            event(f"winch {old.get('state', '-')} -> {s.get('state')}")
        st["status"] = s

    def on_payout(m):
        st["payout"] = float(m.data)

    def on_payload(m):
        st["payload"] = (m.position.x, m.position.y, m.position.z)

    def on_joints(m):
        st["q"] = dict(zip(m.name, m.position))

    def on_image(view):
        def cb(m):
            try:
                img = bridge.imgmsg_to_cv2(m, desired_encoding="bgr8")
            except Exception:                           # noqa: BLE001
                return
            latest[view] = img if img.shape[1] == W else cv2.resize(img, (W, H))
        return cb

    # ---- the claw -------------------------------------------------------- #
    def mechanism():
        """The line and the claw, from winch_ctrl's payout (50 Hz, sim time).

        A line can pull but not push: while the claw rests, payout beyond
        the resting length is slack, and the claw uses the first few mm of
        it to open.
        """
        t = now()
        dt = 0.0 if st["t_mech"] is None else t - st["t_mech"]
        st["t_mech"] = t
        payout, q = st["payout"], st["q"].get("winch_joint", 0.0)
        p = st["payload"]
        on_ground = p is not None and p[2] <= rest_z + 0.002
        under = p is not None and math.hypot(p[0] - geo["x"], p[1] - geo["y"]) < 0.004

        paying_out = payout > st.get("last_payout", 0.0)
        st["last_payout"] = payout
        latched = mode == "latch" and not st["attached"]
        # A payout step can carry the jaws through the whole shut-and-lift in
        # one update; they still pass every angle on the way, so the checks
        # below look at where the claw was resting at the start of it.
        was_resting = st["resting"]
        if latched and payout < 0.05:
            st["phi"] = max(0.0, st["phi"] - dt / CLAW_TAU_S * claw.open_max)
        if not st["resting"]:
            line = payout
            if st["attached"] and on_ground and paying_out:
                st["resting"], st["rest_line"] = True, q
                event(f"payload touched down; claw resting, {q:.3f} m of line out")
            elif not latched:
                # Hanging free, the jaws' own weight shuts the tongs.
                st["phi"] *= math.exp(-dt / CLAW_TAU_S) if dt > 0 else 1.0
        else:
            rest = st["rest_line"]
            slack = payout - rest
            if latched:
                # A latch holds the jaws open; the claw lifts off with them
                # open as soon as the line takes up the top pin's travel.
                st["phi"] += (claw.open_max - st["phi"]) * (
                    1.0 - math.exp(-dt / CLAW_TAU_S) if dt > 0 else 0.0)
                drop = claw.pose(st["phi"])["drop"]
                if slack < drop:
                    st["resting"] = False
                line = max(payout, rest) if slack >= drop else payout
            else:
                # The linkage. Slack lets gravity swing the jaws open (not
                # instantly); taking the slack in pulls them shut in lockstep
                # with the top pin, while the jaws still sit on the eyelet.
                geo_phi = claw.phi_for_drop(max(slack, 0.0))
                if geo_phi < st["phi"]:
                    st["phi"] = geo_phi
                elif dt > 0:
                    st["phi"] += (geo_phi - st["phi"]) * (1.0 - math.exp(-dt / CLAW_TAU_S))
                if slack < 0.0:
                    st["resting"] = False            # shut, and lifting off
                    line = payout
                else:
                    line = rest + claw.pose(st["phi"])["drop"]

        if st["attached"] and st["resting"] and st["phi"] >= claw.release:
            st["attached"] = False
            st["t_release"] = t
            pub_detach.publish(Empty())
            event(f"CLAW OPEN {math.degrees(st['phi']):.0f} deg: the tips clear the "
                  f"eyelet, payload free")
        elif (not st["attached"] and was_resting and st["phi"] < claw.release
              and under and on_ground and mode == "as_drawn"):
            st["attached"] = True
            st["regrabs"] += 1
            pub_attach.publish(Empty())
            event(f"CLAW SHUT ON THE EYELET AGAIN ({math.degrees(st['phi']):.0f} deg) as "
                  f"the line took up the slack: payload re-grabbed")

        deg = math.degrees(st["phi"])
        if not st["attached"]:
            st["claw_note"] = f"open {deg:.0f} deg, payload free"
        elif deg > 0.5:
            st["claw_note"] = (f"closing on the eyelet, {deg:.0f} deg" if st["regrabs"]
                               else f"opening {deg:.0f} deg")
        else:
            st["claw_note"] = ("shut on the eyelet: payload RE-GRABBED" if st["regrabs"]
                               else "shut, holding the eyelet")
        pose = claw.pose(st["phi"])
        for k in pub:
            pub[k].publish(Float64(data=float(pose[k])))
        pub_line.publish(Float64(data=float(line)))
        # The spool turns with the motor: the line it pays out, slack or not.
        pub_spool.publish(Float64(data=-payout / claw_geo["spool_line_r"]))

    # ---- captions and frames -------------------------------------------- #
    def draw_line(img, view):
        cam = geo["cams"].get(view)
        if cam is None:
            return
        q = st["q"].get("winch_joint", 0.0)
        ex = geo["exit"]
        a = cam.project((ex[0], ex[1], alt + ex[2]))
        b = cam.project((geo["top"][0], geo["top"][1], alt + geo["top"][2] - q + 0.004))
        if a and b:
            cv2.line(img, a, b, (35, 35, 35), 1 if view == "wide" else 2, cv2.LINE_AA)

    def caption(img, view):
        s, p = st["status"], st["payload"]
        believes = "released" if s.get("hook_open") else "holding"
        lines = [f"{view}   t = {now():6.2f} s (sim)   claw: {mode.replace('_', ' ')}",
                 f"winch {s.get('state', '-')}   line out {s.get('payout_m', 0):.3f} m",
                 f"winch_ctrl believes: {believes}",
                 f"claw: {st['claw_note']}",
                 (f"payload bottom {p[2] - rest_z:+.3f} m" if p else ""),
                 st["phase"]]
        for i, t in enumerate(lines):
            y = 24 + 22 * i
            cv2.putText(img, t, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (0, 0, 0), 4,
                        cv2.LINE_AA)
            colour = (80, 230, 255) if i == 0 else (255, 255, 255)
            if i == 3:
                colour = (60, 255, 60) if not st["attached"] else (
                    (0, 200, 255) if "opening" in st["claw_note"] else (255, 255, 255))
            cv2.putText(img, t, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.56, colour, 1,
                        cv2.LINE_AA)
        return img

    def write_frames():
        t = now()
        if st["t_written"] is not None and t - st["t_written"] < 1.0 / FPS - 1e-3:
            return
        if not all(v in latest for v in VIEWS):
            return
        st["t_written"] = t
        st.setdefault("t_first_frame", t)
        for v in VIEWS:
            if v not in writers:
                writers[v] = cv2.VideoWriter(str(out / f"{v}.avi"),
                                             cv2.VideoWriter_fourcc(*"MJPG"), FPS, (W, H))
            img = latest[v].copy()
            draw_line(img, v)
            writers[v].write(caption(img, v))
            frames[v] = frames.get(v, 0) + 1

    node.create_subscription(String, "/winch/status", on_status, 10)
    node.create_subscription(Float64, "/winch/gz/payout", on_payout, 10)
    node.create_subscription(Pose, "/sim/payload_pose", on_payload, qos_profile_sensor_data)
    node.create_subscription(JointState, "/bench/joints", on_joints, qos_profile_sensor_data)
    for view in VIEWS:
        node.create_subscription(Image, f"/bench/{view}", on_image(view),
                                 qos_profile_sensor_data)

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
        s, t, pl = st["status"], now(), st["payload"]
        rows.append((round(t, 3), s.get("state"), s.get("payout_m"),
                     st["q"].get("winch_joint"), s.get("hook_open"), st["attached"],
                     round(math.degrees(st["phi"]), 2), pl[2] if pl else None))
        ph = st["phase"]
        if ph == "hanging" and t > 3.0 and s:
            pub_cmd.publish(String(data="lower"))
            st["phase"] = "lowering: the motor pays out line"
            event("command: lower")
        elif ph.startswith("lowering") and s.get("state") == "AT_GROUND":
            pub_cmd.publish(String(data="release"))
            st["phase"] = "down: winch_ctrl records the release"
            st["t_down"] = t
            event("command: release (a gravity hook: bookkeeping only)")
        elif ph.startswith("down") and t - st["t_down"] > 2.0:
            pub_cmd.publish(String(data="stow"))
            st["phase"] = "stowing: the motor winds the claw back up"
            event("command: stow")
        elif ph.startswith("stowing") and s.get("payout_m", 1) <= 1e-3:
            left = pl is not None and pl[2] <= rest_z + 0.01
            st["phase"] = ("stowed: the payload stayed on the ground" if left else
                           "stowed: the PAYLOAD CAME BACK UP with the claw")
            st["t_done"] = t
            event(st["phase"])
        elif ph.startswith("stowed") and t - st["t_done"] > 3.0:
            st["phase"] = "done"

    node.create_timer(0.02, mechanism)
    node.create_timer(1.0 / FPS, tick)
    wall0 = time.time()
    while rclpy.ok() and st["phase"] != "done":
        rclpy.spin_once(node, timeout_sec=0.1)
        if time.time() - wall0 > 60 and (now() == 0.0 or not st["status"]):
            # Fail loudly rather than wait out the wall-clock limit.
            raise SystemExit("no /clock or /winch/status after 60 s: the simulator, "
                             "the bridge or winch_ctrl is not being heard")
        if now() > max_sim_s or time.time() - wall0 > 60 * 40:
            event("timed out")
            break
    for w in writers.values():
        w.release()
    with open(out / "timeline.csv", "w", newline="") as f:
        cw = csv.writer(f)
        cw.writerow(["sim_t", "winch_state", "payout_m", "line_m", "ctrl_believes_open",
                     "payload_attached", "claw_open_deg", "payload_z"])
        cw.writerows(rows)
    (out / "events.txt").write_text("".join(f"{t:7.2f}  {w}\n" for t, w in events))
    node.destroy_node()
    rclpy.shutdown()
    release = next((t for t, w in events if w.startswith("CLAW OPEN")), None)
    return frames, release, st.get("t_first_frame", 0.0)


def encode(out, release_t, first_frame_t):
    for v in VIEWS:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out / f"{v}.avi"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                        str(out / f"{v}.mp4")], check=True)
        (out / f"{v}.avi").unlink()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    *sum((["-i", str(out / f"{v}.mp4")] for v in VIEWS), []),
                    "-filter_complex",
                    "[0:v][1:v]hstack=inputs=2[top];[2:v][3:v]hstack=inputs=2[bot];"
                    "[top][bot]vstack=inputs=2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "22", str(out / "drop.mp4")], check=True)
    if release_t is not None:
        start = max(0.0, release_t - first_frame_t - 3.0)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.2f}",
                        "-t", "9", "-i", str(out / "claw.mp4"), "-vf", "setpts=4.0*PTS",
                        "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                        str(out / "claw_release_4x_slow.mp4")], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--alt", type=float, default=5.0, help="airframe height, m")
    ap.add_argument("--payload", type=float, nargs=3, default=(0.10, 0.05, 0.05),
                    metavar=("X", "Y", "Z"), help="payload box, m (rulebook Fig. 1)")
    ap.add_argument("--claw", choices=("as_drawn", "latch"), default="as_drawn")
    ap.add_argument("--out", type=Path, default=ROOT / "logs" / "winch_bench")
    ap.add_argument("--max-sim-s", type=float, default=90.0)
    args = ap.parse_args()

    out = args.out.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    models, upstream, airframe = build_vehicle(out)
    geo = rig_geometry(args.alt, args.payload, airframe["claw"])
    write_world(out, args.alt, args.payload, geo)
    write_bridge(out)

    env = dict(os.environ,
               GZ_SIM_RESOURCE_PATH=os.pathsep.join(
                   [str(models), upstream, os.environ.get("GZ_SIM_RESOURCE_PATH", "")]),
               GZ_PARTITION=f"winch_bench_{os.getpid()}", GZ_IP="127.0.0.1",
               ROS_DOMAIN_ID=os.environ.get("ROS_DOMAIN_ID", "61"),
               # Everything runs on this host: shared memory only. When WSL
               # falls back to its "None" networking mode, UDP discovery on
               # the loopback stops working and every node runs deaf.
               FASTDDS_BUILTIN_TRANSPORTS="SHM")
    env.pop("ROS_LOCALHOST_ONLY", None)
    os.environ.pop("ROS_LOCALHOST_ONLY", None)
    os.environ.update({k: env[k] for k in ("GZ_PARTITION", "GZ_IP", "ROS_DOMAIN_ID",
                                           "FASTDDS_BUILTIN_TRANSPORTS")})
    procs = []

    def start(cmd, log):
        procs.append(subprocess.Popen(cmd, env=env, stdout=open(out / log, "w"),
                                      stderr=subprocess.STDOUT, start_new_session=True))

    try:
        start(["gz", "sim", "-s", "-r", "--headless-rendering", str(out / "world.sdf")],
              "gz.log")
        start(["ros2", "run", "ros_gz_bridge", "parameter_bridge", "--ros-args",
               "-p", f"config_file:={out / 'bridge.yaml'}"], "bridge.log")
        # winch_ctrl's payout goes to the bench (the claw's mechanics), not
        # straight to the joint; its own detach is not bridged: the claw lets go.
        start([sys.executable, "-c", "from winch_ctrl.winch_node import main; main()",
               "--ros-args", "-p", "backend:=gazebo", "-p", "use_sim_time:=true",
               # 5 Hz is 9 cm steps of line at stow speed: too coarse to film.
               "-p", "publish_rate_hz:=25.0"],
              "winch.log")
        frames, release_t, first_t = run_drop(out, args.alt, args.payload, geo, airframe["claw"],
                                     args.claw, args.max_sim_s)
    finally:
        for sig in (signal.SIGINT, signal.SIGKILL):
            for p in procs:
                try:
                    os.killpg(p.pid, sig)
                except ProcessLookupError:
                    pass
            time.sleep(2)

    print(f"frames: {frames}")
    encode(out, release_t, first_t)
    print((out / "events.txt").read_text())
    print(f"outputs in {out}")


if __name__ == "__main__":
    main()
