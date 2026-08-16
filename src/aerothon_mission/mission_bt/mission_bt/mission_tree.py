#!/usr/bin/env python3
"""Mission 2 (SkyScan) behaviour tree — RUNNABLE (drives ArduPilot via MAVROS).

Root (Fallback)
├── Guard (Sequence): CriticalOK -> else StageAwareAbort
└── Mission (Sequence): SetModeArm -> Takeoff -> ScanStartQR -> GotoCorridor
    -> Corridor(avoid) -> GotoZone -> Climb10 -> LawnmowerSearch
    -> WinchDrop -> ReturnCorridor(avoid) -> Land

Waypoints are local-ENU metres from the takeoff origin (params, so tunable /
sim-vs-real). The corridor + return hand control to the avoidance node
(velocity setpoints); every other leg streams GPS position setpoints.
"""

import math
import rclpy
from rclpy.node import Node
import py_trees
try:
    import py_trees_ros
except ImportError:
    py_trees_ros = None
from std_msgs.msg import Bool, String

from mission_bt.mav_commander import Mav


# --------------------------------------------------------------------------- #
# Guard & Abort
# --------------------------------------------------------------------------- #
class CheckAbortTriggered(py_trees.behaviour.Behaviour):
    """Returns SUCCESS when an abort condition trips, triggering StageAwareAbort."""
    def __init__(self, mav, node):
        super().__init__("CheckAbortTriggered")
        self.mav = mav
        self.node = node

    def _trip(self, reason):
        self.feedback_message = reason
        if not self.mav.abort_latched:
            self.mav.abort_reason = reason
            self.mav.abort_latched = True
        return py_trees.common.Status.SUCCESS

    def update(self):
        # An abort that un-aborts itself is not an abort. Every condition below
        # is level-triggered — attitude recovers once RTL levels the aircraft,
        # battery voltage recovers under reduced load, the FCU reconnects — so
        # without this latch the mission resumed from its previous leg while
        # the aircraft was already flying itself home.
        if self.mav.abort_latched:
            self.feedback_message = f"latched: {self.mav.abort_reason}"
            return py_trees.common.Status.SUCCESS

        # Pre-flight disconnects and battery telemetry must not trigger LAND.
        # The abort guard becomes authoritative once the mission starts or the
        # aircraft is armed.
        if not self.mav.mission_started and not self.mav.state.armed:
            return py_trees.common.Status.FAILURE
        # Trigger abort if connection lost, abort topic flagged, or critical battery.
        if not self.mav.connected():
            return self._trip("FCU disconnected")
        if self.mav.abort_requested:
            return self._trip("Abort requested")
        if self.mav.battery_critical():
            return self._trip("Battery critical")
        # An aircraft held past its attitude limit is not flying the mission,
        # it is falling into something. The previous live run sat at 54 deg
        # against a corridor wall and the tree happily reported GOTO_CORRIDOR.
        if self.mav.attitude_excessive():
            return self._trip(
                f"Excessive attitude "
                f"(roll={self.mav.roll_deg:.1f} pitch={self.mav.pitch_deg:.1f})")
        return py_trees.common.Status.FAILURE


class StageAwareAbort(py_trees.behaviour.Behaviour):
    def __init__(self, mav):
        super().__init__("StageAwareAbort")
        self.mav = mav
        self._command_sent = False

    def initialise(self):
        self._command_sent = False

    def update(self):
        if self._command_sent:
            return py_trees.common.Status.RUNNING
        self.mav.enable_avoidance(False)
        reason = self.mav.abort_reason or "unspecified"
        # In near-ground conditions, land immediately; otherwise RTL
        if self.mav.alt() < 1.5:
            self.mav.land()
            self.logger.warning("ABORT -> LAND (low alt)")
            self.mav.publish_result("ABORTED_LAND", reason)
        else:
            self.mav.set_mode("RTL")
            self.logger.warning("ABORT -> RTL")
            self.mav.publish_result("ABORTED_RTL", reason)
        self._command_sent = True
        return py_trees.common.Status.RUNNING


# --------------------------------------------------------------------------- #
# Mission leaves
# --------------------------------------------------------------------------- #
class WaitForMissionStart(py_trees.behaviour.Behaviour):
    """Hold in a safe, disarmed state until the GCS explicitly starts M2."""
    def __init__(self, mav):
        super().__init__("WaitForMissionStart")
        self.mav = mav

    def update(self):
        self.feedback_message = "waiting for GCS start" if not self.mav.mission_started else "start received"
        return (py_trees.common.Status.SUCCESS if self.mav.mission_started
                else py_trees.common.Status.RUNNING)


class SetModeArm(py_trees.behaviour.Behaviour):
    def __init__(self, mav):
        super().__init__("SetModeArm"); self.mav = mav; self._t = 0

    def update(self):
        self._t += 1
        if self.mav.state.mode != "GUIDED":
            self.mav.set_mode("GUIDED"); return py_trees.common.Status.RUNNING
        if not self.mav.state.armed:
            if self._t % 10 == 0:
                self.mav.arm(True)
            return py_trees.common.Status.RUNNING
        return py_trees.common.Status.SUCCESS


class Takeoff(py_trees.behaviour.Behaviour):
    def __init__(self, mav, alt):
        super().__init__("Takeoff"); self.mav = mav; self.alt = alt; self._sent = False

    def initialise(self):
        self._sent = False

    def update(self):
        if not self._sent:
            self.mav.takeoff(self.alt); self._sent = True
        return (py_trees.common.Status.SUCCESS
                if self.mav.alt() > self.alt - 0.5
                else py_trees.common.Status.RUNNING)


class ScanStartQR(py_trees.behaviour.Behaviour):
    """Hold at scan pose; capture the decoded target.

    KNOWN DEFECT (closed in Phase 3, see PHASE_PLAN.md): this times out to
    SUCCESS with an empty target string, so an undecoded start QR does not
    stop the mission. Left intact in Phase 0 only because the camera is not
    yet commanded nadir (Phase 2) — fixing the gate before the camera points
    at the QR would block every run.
    """
    def __init__(self, mav, pose, timeout_ticks=80):
        super().__init__("ScanStartQR"); self.mav = mav
        self.pose = pose; self.timeout = timeout_ticks; self._t = 0

    def initialise(self): self._t = 0

    def update(self):
        self._t += 1
        self.mav.goto(*self.pose)
        if self.mav.qr_decoded:
            self.mav.set_target(self.mav.qr_decoded)
            self.feedback_message = f"target={self.mav.qr_decoded}"
            return py_trees.common.Status.SUCCESS
        return (py_trees.common.Status.SUCCESS if self._t > self.timeout
                else py_trees.common.Status.RUNNING)


class Goto(py_trees.behaviour.Behaviour):
    def __init__(self, name, mav, x, y, z, yaw=0.0, tol=0.6):
        super().__init__(name); self.mav = mav
        self.x, self.y, self.z, self.yaw, self.tol = x, y, z, yaw, tol

    def update(self):
        self.mav.goto(self.x, self.y, self.z, self.yaw)
        return (py_trees.common.Status.SUCCESS
                if self.mav.reached(self.x, self.y, self.z, self.tol)
                else py_trees.common.Status.RUNNING)


class Corridor(py_trees.behaviour.Behaviour):
    """Hand control to the avoidance node until past exit_x (local ENU)."""
    def __init__(self, name, mav, exit_x, forward=True):
        super().__init__(name); self.mav = mav
        self.exit_x = exit_x; self.forward = forward

    def update(self):
        self.mav.enable_avoidance(True)
        px = self.mav.pos()[0]
        done = px > self.exit_x if self.forward else px < self.exit_x
        if done:
            self.mav.enable_avoidance(False)
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.RUNNING


class LawnmowerSearch(py_trees.behaviour.Behaviour):
    def __init__(self, mav, zone, alt, spacing=6.0):
        super().__init__("LawnmowerSearch"); self.mav = mav
        self.alt = alt
        self.wps = self._plan(zone, spacing)
        self.i = 0

    @staticmethod
    def _plan(zone, spacing):
        x0, x1, y0, y1 = zone
        wps, flip = [], False
        y = y0
        while y <= y1:
            xs = [x1, x0] if flip else [x0, x1]
            wps += [(xs[0], y), (xs[1], y)]
            y += spacing; flip = not flip
        return wps

    def initialise(self):
        self.i = 0

    def update(self):
        if self.mav.qr_matched:
            return py_trees.common.Status.SUCCESS
        if self.i >= len(self.wps):
            return py_trees.common.Status.FAILURE     # swept all, no match
        wx, wy = self.wps[self.i]
        self.mav.goto(wx, wy, self.alt)
        if self.mav.reached(wx, wy, self.alt, tol=0.8):
            self.i += 1
        return py_trees.common.Status.RUNNING


class WinchDrop(py_trees.behaviour.Behaviour):
    """Descend to 5 m over the matched QR, lower + release, climb back."""
    def __init__(self, mav, drop_alt=5.0, cruise_alt=10.0):
        super().__init__("WinchDrop"); self.mav = mav
        self.drop_alt = drop_alt; self.cruise_alt = cruise_alt
        self.drop_x = 0.0; self.drop_y = 0.0
        self.phase = 0; self._t = 0

    def initialise(self):
        self.phase = 0
        self._t = 0
        # Latch current horizontal coordinates to prevent drift during descent
        self.drop_x, self.drop_y = self.mav.pos()[:2]

    def update(self):
        if self.phase == 0:                            # descend
            self.mav.goto(self.drop_x, self.drop_y, self.drop_alt)
            if self.mav.reached(self.drop_x, self.drop_y, self.drop_alt, 0.5):
                self.phase = 1; self._t = 0
        elif self.phase == 1:                          # lower + release
            self.mav.goto(self.drop_x, self.drop_y, self.drop_alt)
            self.mav.winch("lower"); self._t += 1
            if self._t > 20:
                self.mav.winch("release"); self.phase = 2; self._t = 0
        elif self.phase == 2:                          # climb back
            self.mav.winch("stow")
            self.mav.goto(self.drop_x, self.drop_y, self.cruise_alt)
            if self.mav.reached(self.drop_x, self.drop_y, self.cruise_alt, 0.6):
                return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.RUNNING


class Land(py_trees.behaviour.Behaviour):
    def __init__(self, mav):
        super().__init__("Land"); self.mav = mav

    def initialise(self):
        # Tell the commander that the coming disarm is ours, so the external
        # intervention watchdog does not read a normal landing as a takeover.
        self.mav.expect_disarm(True)

    def update(self):
        self.mav.land()
        if self.mav.state.armed:
            return py_trees.common.Status.RUNNING
        self.mav.publish_result("COMPLETED", "landed and disarmed")
        return py_trees.common.Status.SUCCESS


# --------------------------------------------------------------------------- #
def build_root(mav, node, p):
    root = py_trees.composites.Selector(name="Root", memory=False)
    
    # Guard sequence: only ticks StageAwareAbort when CheckAbortTriggered succeeds
    abort_branch = py_trees.composites.Sequence(name="AbortBranch", memory=False)
    abort_branch.add_children([CheckAbortTriggered(mav, node), StageAwareAbort(mav)])

    mission = py_trees.composites.Sequence(name="Mission", memory=True)
    mission.add_children([
        WaitForMissionStart(mav),
        SetModeArm(mav),
        Takeoff(mav, p['takeoff_alt']),
        ScanStartQR(mav, p['scan_pose']),
        Goto("GotoCorridor", mav, *p['corridor_entry']),
        Corridor("Corridor", mav, p['corridor_exit_x'], forward=True),
        Goto("GotoZone", mav, *p['zone_entry']),
        Goto("Climb10", mav, p['zone_entry'][0], p['zone_entry'][1], p['search_alt']),
        LawnmowerSearch(mav, p['zone'], p['search_alt']),
        WinchDrop(mav, p['drop_alt'], p['search_alt']),
        Goto("ReturnToCorridor", mav, *p['corridor_return_entry']),
        Corridor("ReturnCorridor", mav, p['corridor_return_exit_x'], forward=False),
        Goto("GotoHome", mav, *p['home']),
        Land(mav),
    ])
    root.add_children([abort_branch, mission])
    return root


def apply_pending_reset(root, mav):
    """Fail-closed rail: return the tree to WAITING after an intervention.

    A py_trees Sequence with memory=True retains its child index, so an
    external LAND/DISARM previously left the mission "stuck" at whatever leg
    it had reached — the last live run reported GOTO_CORRIDOR while sitting
    disarmed on the ground. Invalidating the root forces every leaf back
    through initialise() on the next tick.

    Returns the reset reason if one was applied, else None.
    """
    reason = mav.consume_reset()
    if reason is None:
        return None
    mav.publish_result("INTERRUPTED", reason)
    root.stop(py_trees.common.Status.INVALID)
    return reason


def main():
    rclpy.init()
    node = Node("mission_bt")

    # Waypoints in local-ENU metres from takeoff origin (declare as params).
    defaults = {
        'takeoff_alt': 5.0, 'search_alt': 10.0, 'drop_alt': 5.0,
        'scan_pose': (0.0, 0.0, 5.0),
        'corridor_entry': (5.0, 0.0, 3.0),
        'corridor_exit_x': 15.5,
        'zone_entry': (18.0, 0.0, 3.0),
        'zone': (20.0, 52.0, -12.0, 12.0),
        'corridor_return_entry': (15.0, 0.0, 3.0, math.pi),
        'corridor_return_exit_x': 4.5,
        'home': (0.0, 0.0, 5.0),
    }
    mav = Mav(node)
    tree = py_trees.trees.BehaviourTree(build_root(mav, node, defaults))
    tree.setup(timeout=15.0)
    state_pub = node.create_publisher(String, "/mission/state", 10)
    state_names = {
        "WaitForMissionStart": "WAITING", "SetModeArm": "ARMING",
        "Takeoff": "TAKEOFF", "ScanStartQR": "START_QR",
        "GotoCorridor": "GOTO_CORRIDOR", "Corridor": "CORRIDOR_NAV",
        "GotoZone": "ENTER_ZONE", "Climb10": "ENTER_ZONE",
        "LawnmowerSearch": "SEARCH_QR", "WinchDrop": "WINCH_DROP",
        "ReturnToCorridor": "RETURN", "ReturnCorridor": "RETURN_CORRIDOR",
        "GotoHome": "RETURN", "Land": "LAND", "StageAwareAbort": "ABORT",
    }
    last_state = {"value": ""}

    def tick_tree():
        # BehaviourTree.tick_tock() blocks forever. Running it before
        # rclpy.spin() previously prevented every subscription, service
        # response and setpoint timer in this node from being processed.
        tree.tick()
        tip = tree.tip()
        state = state_names.get(tip.name if tip else "", "IDLE")

        # Consume interventions *after* ticking so the Land leaf still gets to
        # observe its own disarm and latch COMPLETED before we reset.
        reset_reason = apply_pending_reset(tree.root, mav)
        if reset_reason is not None:
            node.get_logger().warning(f"Mission tree reset: {reset_reason}")
            state = "WAITING"

        state_pub.publish(String(data=state))
        if state != last_state["value"]:
            node.get_logger().info(f"Mission state -> {state}")
            last_state["value"] = state

    node.create_timer(0.2, tick_tree)   # 5 Hz without blocking ROS callbacks

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        tree.shutdown(); node.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    main()
