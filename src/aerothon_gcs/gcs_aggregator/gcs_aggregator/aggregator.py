#!/usr/bin/env python3
"""GCS aggregator — RUNNABLE.

Bridges the ROS 2 graph to the Tauri control GCS over WebSocket:
  outbound  kind=telemetry (10 Hz snapshot) / kind=event / kind=ack
  inbound   kind=command   -> arm/disarm, set_mode, abort, set target

MAVROS supplies flight data as ROS topics, so this node speaks only ROS.
Camera is a SEPARATE MJPEG stream (web_video_server).
"""
import asyncio
import json
import math
import time
import threading

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile
from mavros_msgs.msg import State
from mavros_msgs.srv import CommandBool, SetMode, CommandTOL
from sensor_msgs.msg import BatteryState, NavSatFix, LaserScan
from geometry_msgs.msg import PoseStamped, Vector3, TwistStamped
from nav_msgs.msg import OccupancyGrid
from std_msgs.msg import String, Bool, Float32, Float64

import websockets


def _euler_deg(q):
    """Quaternion -> (roll, pitch, yaw) in degrees."""
    sinr = 2 * (q.w * q.x + q.y * q.z)
    cosr = 1 - 2 * (q.x * q.x + q.y * q.y)
    roll = math.atan2(sinr, cosr)
    sinp = 2 * (q.w * q.y - q.z * q.x)
    pitch = math.asin(max(-1.0, min(1.0, sinp)))
    siny = 2 * (q.w * q.z + q.x * q.y)
    cosy = 1 - 2 * (q.y * q.y + q.z * q.z)
    yaw = math.atan2(siny, cosy)
    return math.degrees(roll), math.degrees(pitch), (math.degrees(yaw) + 360) % 360

SCHEMA_VERSION = 1
WS_HOST, WS_PORT = "0.0.0.0", 8765
TELEM_HZ = 10.0


class Aggregator(Node):
    def __init__(self):
        super().__init__("gcs_aggregator")
        self._ws_clients = set()
        self._loop = None
        self.state = self._blank_state()

        self._arm_t = None
        q = 10
        qos_sensor = qos_profile_sensor_data
        self.create_subscription(State, "/mavros/state", self._on_state, qos_sensor)
        self.create_subscription(BatteryState, "/mavros/battery", self._on_batt, qos_sensor)
        self.create_subscription(PoseStamped, "/mavros/local_position/pose", self._on_pose, qos_sensor)
        self.create_subscription(TwistStamped, "/mavros/local_position/velocity_local", self._on_vel, qos_sensor)
        self.create_subscription(LaserScan, "/scan", self._on_scan, qos_sensor)
        self.create_subscription(NavSatFix, "/mavros/global_position/global", self._on_gps, qos_sensor)
        self.create_subscription(String, "/percep/qr/decoded", self._on_qr, q)
        self.create_subscription(Bool, "/percep/qr/matched", self._on_match, q)
        self.create_subscription(Vector3, "/percep/banner", self._on_banner, q)
        self.create_subscription(Bool, "/percep/redzone", self._on_red, q)
        self.create_subscription(Vector3, "/avoidance/status", self._on_avoid, q)
        self.create_subscription(Bool, "/mission_ready", self._on_ready, q)
        self.create_subscription(String, "/mission/state", self._on_mission_state, q)
        # Real slam_toolbox occupancy grid (throttled + downsampled to the GCS).
        self._last_map = 0.0
        self.create_subscription(OccupancyGrid, "/map", self._on_map, 1)

        self.pub_abort = self.create_publisher(Bool, "/mission/abort", q)
        self.pub_start = self.create_publisher(Bool, "/mission/start", q)
        self.pub_target = self.create_publisher(String, "/mission/target", q)
        self.pub_winch = self.create_publisher(String, "/winch/cmd", q)
        self.pub_gimbal_pitch = self.create_publisher(Float64, "/gimbal/cmd_pitch", q)

        self.cli_arm = self.create_client(CommandBool, "/mavros/cmd/arming")
        self.cli_mode = self.create_client(SetMode, "/mavros/set_mode")
        self.cli_takeoff = self.create_client(CommandTOL, "/mavros/cmd/takeoff")
        self.cli_land = self.create_client(CommandTOL, "/mavros/cmd/land")

        self.create_timer(1.0 / TELEM_HZ, self._publish_snapshot)
        self.get_logger().info(f"aggregator up; ws://{WS_HOST}:{WS_PORT}")

    @staticmethod
    def _blank_state():
        return {
            "mission": {"selected": None, "state": "idle", "armed": False, "mode": "", "elapsed": 0.0},
            "flight": {"x": 0, "y": 0, "alt": 0, "gs": 0,
                       "roll_deg": 0, "pitch_deg": 0, "yaw_deg": 0},
            "gps": {"lat": 0, "lon": 0, "sats": 0, "fix": "NO"},
            "power": {"volt": 0, "pct": 0},
            "nav": {"front_m": 0, "centering_err": 0, "cmd_vx": 0},
            "percep": {"start_qr": "", "target_match": False, "banner": False,
                       "redzone_visible": False},
            "safety": {"ready": False, "fcu_connected": False, "ekf": True,
                       "geofence": "INSIDE", "battery_ok": True},
            "checklist": {k: False for k in
                          ("takeoff", "start_qr", "banner", "corridor",
                           "target_id", "drop", "return", "land")},
            "scan": {"yaw_deg": 0, "ranges": []},
            "gimbal": {"pitch_deg": 0.0},
        }

    # ---- subscription callbacks ---- #
    def _on_state(self, m):
        self.state["safety"]["fcu_connected"] = bool(m.connected)
        if m.armed and self._arm_t is None:
            self._arm_t = time.time()
        elif not m.armed:
            self._arm_t = None
        self.state["mission"]["armed"] = m.armed
        self.state["mission"]["mode"] = m.mode
        self.state["mission"]["elapsed"] = round(time.time() - self._arm_t, 1) if self._arm_t else 0.0

    def _on_batt(self, m):
        self.state["power"]["volt"] = round(m.voltage, 2)
        self.state["power"]["pct"] = round(m.percentage * 100) if m.percentage <= 1.0 else round(m.percentage)
        self.state["safety"]["battery_ok"] = not (0.0 < m.voltage < 10.5 or 0.0 < m.percentage < 0.15)

    def _on_pose(self, m):
        p = m.pose.position
        roll, pitch, yaw = _euler_deg(m.pose.orientation)
        fl = self.state["flight"]
        fl["x"], fl["y"], fl["alt"] = round(p.x, 2), round(p.y, 2), round(p.z, 2)
        fl["roll_deg"], fl["pitch_deg"], fl["yaw_deg"] = round(roll, 1), round(pitch, 1), round(yaw, 1)
        self.state["scan"]["yaw_deg"] = round(yaw, 1)

    def _on_vel(self, m):
        self.state["flight"]["gs"] = round(math.hypot(m.twist.linear.x, m.twist.linear.y), 2)

    def _on_scan(self, m):
        n = len(m.ranges)
        if not n:
            return
        step = max(1, n // 72)
        out = []
        for i in range(0, n, step):
            r = m.ranges[i]
            out.append(round(r, 2) if (math.isfinite(r) and m.range_min < r < m.range_max) else None)
        self.state["scan"]["ranges"] = out

    def _on_gps(self, m):
        self.state["gps"]["lat"] = m.latitude
        self.state["gps"]["lon"] = m.longitude
        self.state["gps"]["fix"] = "3D" if m.status.status >= 0 else "NO"

    def _on_qr(self, m):
        self.state["percep"]["start_qr"] = m.data
        if m.data:
            self.state["checklist"]["start_qr"] = True

    def _on_match(self, m):
        self.state["percep"]["target_match"] = m.data
        if m.data:
            self.state["checklist"]["target_id"] = True

    def _on_banner(self, m):
        det = m.z > 0.5
        self.state["percep"]["banner"] = det
        if det:
            self.state["checklist"]["banner"] = True

    def _on_red(self, m):
        self.state["percep"]["redzone_visible"] = m.data

    def _on_avoid(self, m):
        self.state["nav"] = {"front_m": round(m.x, 2),
                             "centering_err": round(m.y, 2), "cmd_vx": round(m.z, 2)}

    def _on_ready(self, m):
        self.state["safety"]["ready"] = m.data

    def _on_mission_state(self, m):
        self.state["mission"]["state"] = m.data
        if m.data == "TAKEOFF":
            self.state["checklist"]["takeoff"] = True
        elif m.data == "CORRIDOR_NAV":
            self.state["checklist"]["corridor"] = True
        elif m.data in {"RETURN", "RETURN_CORRIDOR"}:
            self.state["checklist"]["return"] = True
        elif m.data == "LAND":
            self.state["checklist"]["land"] = True

    def _on_map(self, m):
        """Forward the REAL slam_toolbox occupancy grid (throttled + downsampled)."""
        now = time.time()
        if now - self._last_map < 1.0:
            return
        self._last_map = now
        w, h, data = m.info.width, m.info.height, m.data
        if not w or not h:
            return
        step = max(1, max(w, h) // 120)          # cap output ~120 cells/side
        ow, oh = (w + step - 1) // step, (h + step - 1) // step
        out = [-1] * (ow * oh)
        for r in range(0, h, step):
            orow = (r // step) * ow
            for c in range(0, w, step):
                best = -1                         # max-pool so obstacles survive
                for dr in range(step):
                    rr = r + dr
                    if rr >= h:
                        break
                    rb = rr * w
                    for dc in range(step):
                        cc = c + dc
                        if cc >= w:
                            break
                        v = data[rb + cc]
                        if v > best:
                            best = v
                out[orow + c // step] = int(best)
        grid = {"res": round(m.info.resolution * step, 3), "w": ow, "h": oh,
                "ox": round(m.info.origin.position.x, 3),
                "oy": round(m.info.origin.position.y, 3), "data": out}
        self._broadcast(self._env("map", grid))

    # ---- outbound ---- #
    def _env(self, kind, data):
        return json.dumps({"v": SCHEMA_VERSION, "kind": kind, "t": time.time(), "data": data})

    def _publish_snapshot(self):
        self._broadcast(self._env("telemetry", self.state))

    def _broadcast(self, payload):
        if self._loop and self._ws_clients:
            asyncio.run_coroutine_threadsafe(self._bcast(payload), self._loop)

    async def _bcast(self, msg):
        dead = set()
        for ws in self._ws_clients:
            try:
                await ws.send(msg)
            except Exception:
                dead.add(ws)
        self._ws_clients -= dead

    # ---- inbound commands ---- #
    async def _handler(self, ws):
        self._ws_clients.add(ws)
        try:
            async for raw in ws:
                await self._on_command(ws, raw)
        finally:
            self._ws_clients.discard(ws)

    async def _on_command(self, ws, raw):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return
        if msg.get("kind") != "command":
            return
        d = msg.get("data", {})
        cmd, cid = d.get("cmd"), d.get("cmd_id")
        result, reason = self._dispatch(cmd, d.get("args", {}))
        await ws.send(self._env("ack", {"cmd_id": cid, "cmd": cmd,
                                        "result": result, "reason": reason}))

    def _dispatch(self, cmd, args):
        try:
            # Flight-changing commands must never bypass the readiness
            # interlock. Abort / land / RTL remain available when unhealthy.
            if cmd in {"arm", "takeoff", "start_mission"} and not self.state["safety"]["ready"]:
                return "rejected", "mission interlock not ready"
            if cmd == "arm":
                self.cli_arm.call_async(CommandBool.Request(value=True))
            elif cmd == "disarm":
                self.cli_arm.call_async(CommandBool.Request(value=False))
            elif cmd == "set_mode":
                r = SetMode.Request(); r.custom_mode = args.get("mode", "GUIDED")
                self.cli_mode.call_async(r)
            elif cmd == "takeoff":
                alt = float(args.get("alt", 5.0))
                self.cli_takeoff.call_async(CommandTOL.Request(altitude=alt))
            elif cmd == "land":
                if self.cli_land.service_is_ready():
                    self.cli_land.call_async(CommandTOL.Request())
                else:
                    self.cli_mode.call_async(SetMode.Request(custom_mode="LAND"))
            elif cmd == "winch":
                action = args.get("action", "stow")
                self.pub_winch.publish(String(data=action))
            elif cmd == "gimbal_pitch":
                pitch_deg = max(-90.0, min(30.0, float(args.get("degrees", 0.0))))
                self.pub_gimbal_pitch.publish(Float64(data=math.radians(pitch_deg)))
                self.state["gimbal"]["pitch_deg"] = round(pitch_deg, 1)
            elif cmd == "abort":
                self.pub_abort.publish(Bool(data=True))
            elif cmd == "start_mission":
                self.state["mission"]["selected"] = "M2"
                self.state["mission"]["state"] = "STARTING"
                self.pub_start.publish(Bool(data=True))
            elif cmd == "set_target":
                self.pub_target.publish(String(data=args.get("target", "")))
            else:
                return "rejected", "unknown cmd"
            return "accepted", ""
        except Exception as e:  # noqa: BLE001
            return "rejected", str(e)

    def start_ws(self):
        def run():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(websockets.serve(self._handler, WS_HOST, WS_PORT))
            self._loop.run_forever()
        threading.Thread(target=run, daemon=True).start()


def main():
    rclpy.init()
    node = Aggregator()
    node.start_ws()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    main()
