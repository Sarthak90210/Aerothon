#!/usr/bin/env python3
"""The return slalom's 1.0 m slot: keep the reserve, and get back out when inside.

final_mission_r12 and r13 (24 Oct 2026): world 'shipped''s return slalom
leaves a 1.0 m slot beside its second block against the simulation's
2 x 0.45 m. Approaching it the planner took the straight line, or the
zero-reserve route, 0.450-0.457 m from the block corner although a route
keeping the 2.5 cm sampling reserve existed. Lidar noise then put the
aircraft 1 cm inside the clearance and it could not get out:

  * every command, the planned recentre sidestep included, was certified
    against 0.45 m along its whole predicted motion -- the start point
    already failed it;
  * the nose lidar (0.139 m ahead) cannot see the strip beside the body
    centre through the masked rear sector, so every sideways step of more
    than 2.5 cm was "unobserved" as well.

Drift took the clearance to 0.41 m and the navigator gave up STUCK at
x=9.94 (r10 had passed the same slot 3 cm off centre).

Now the sampling-reserve routes (including a lattice shifted half a cell)
come before the bare-limit straight line; the sidestep is certified against
the band it was planned in and must end with more clearance; and 5 cm either
side of the body-to-sensor link, inside the central airframe, counts as
observed. Wider blind sideways travel stays refused.

    source /opt/ros/jazzy/setup.bash
    python3 -m pytest sim/test_return_slot_recentre_motion.py -v
"""

import base64
import json
import math
import os
import struct
import sys
import unittest
import zlib
from types import SimpleNamespace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src", "aerothon_avoidance", "avoidance"))
sys.path.insert(0, HERE)

import rclpy                                        # noqa: E402
from geometry_msgs.msg import PoseStamped           # noqa: E402
from rclpy.parameter import Parameter               # noqa: E402
from sensor_msgs.msg import LaserScan               # noqa: E402

from avoidance.fast_connected_planner_candidate import (  # noqa: E402
    RECENTRE_SLACK, SAMPLING_RESERVE, FastConnectedPlanner)
from avoidance.velocity_controller import VelocityController  # noqa: E402
from test_narrow_slot_recentre import slalom        # noqa: E402
# The module, not its TestCase: an imported class would be collected again.
import test_slalom_traverse as slalom_module        # noqa: E402
from test_slalom_traverse import rect, scan_at      # noqa: E402

CLEARANCE = 0.45                 # world_sim_venue.yaml passage_half_width
AIRFRAME_R = 0.4                 # VelocityController airframe_radius
MOUNT = (0.139, -0.002)          # base_link -> base_scan, the CAD/sim mount
# Recorded r10/r12 scans approaching block 2's slot; provenance inside.
FIXTURE = os.path.join(HERE, "fixtures", "return_slot_reserve_shipped_20261024.json")

# World 'shipped' return lane, home-local (world + (3.5, -2.0)): walls'
# inner faces at y -3.5 and -5.5, the blocks from r12's layout.json.
R12_RECTS = [rect(11.0, -3.45, 6.0, 0.1), rect(11.0, -5.55, 6.0, 0.1),
             (11.925, 12.275, -5.5, -4.5),   # block 1: slot y -4.5..-3.5
             (9.525, 9.875, -4.5, -3.5)]     # block 2: slot y -5.5..-4.5
# Where r12 stalled: heading west at the mouth of block 2's slot, 6 cm
# north of its centre line and just inside 0.45 m of the block's corner.
R12_STALL = (9.92, -4.94)
# 1-2 cm inside the clearance there, as r12/r13 observed it (0.435-0.444).
INSIDE = [(9.96, -4.93), (9.95, -4.92)]

CONDITIONING = {'range_min_valid': 0.15, 'range_max_valid': 12.0,
                'mask_sectors_deg': [150.0, 210.0], 'median_window': 3}


def conditioned(scan):
    """VelocityController.conditioned with its default parameters."""
    return VelocityController.conditioned(SimpleNamespace(_g=CONDITIONING.get), scan)


def mounted_planner(scan):
    """The controller's planner on a base_scan capture from the nose mount."""
    bearings, ranges = conditioned(scan)
    p = FastConnectedPlanner(CLEARANCE, clearance_floor=CLEARANCE, occupied_radius=AIRFRAME_R)
    p.observe(bearings, ranges, 12.0, sensor_origin=MOUNT, hits=ranges < 12.0 - 0.001)
    return p


def mounted_scan(x, y, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return scan_at(x + c * MOUNT[0] - s * MOUNT[1], y + s * MOUNT[0] + c * MOUNT[1], yaw, R12_RECTS)


def route_clearance(p, path, near=0.1, far=2.0):
    """Least observed clearance along the planned route between `near` and `far` m ahead."""
    dense = np.concatenate([np.linspace(a, b, 80) for a, b in zip(np.array(path[:-1]), np.array(path[1:]))])
    reach = np.linalg.norm(dense, axis=1)
    return float(p.distances(dense[(reach >= near) & (reach <= far)]).min())


class RecentreCertificateTests(unittest.TestCase):
    """Planner side: what the sidestep certificate accepts."""

    def setUp(self):
        self.p = FastConnectedPlanner(CLEARANCE, clearance_floor=CLEARANCE, occupied_radius=0.025)
        self.p.observe(*slalom(0.06))            # 0.43 m from the slot's left side
        self.assertEqual(self.p.plan(0.0), [])
        self.ux, self.uy = self.p.recentre

    def test_a_short_move_out_along_the_gradient_is_certified(self):
        out = [(0.0, 0.0), (0.02 * self.ux, 0.02 * self.uy), (0.04 * self.ux, 0.04 * self.uy)]
        self.assertFalse(self.p.polyline_clear(out), 'the full certificate refuses it')
        self.assertTrue(self.p.recentre_clear(out))

    def test_a_move_that_ends_closer_is_refused(self):
        toward = [(0.0, 0.0), (-0.01 * self.ux, -0.01 * self.uy)]
        self.assertFalse(self.p.recentre_clear(toward))

    def test_a_move_that_leaves_the_band_is_refused(self):
        here = float(self.p.distances([(0, 0)])[0])
        dip = here - (CLEARANCE - RECENTRE_SLACK) + 0.01
        out = [(0.0, 0.0), (-dip * self.ux, -dip * self.uy), (0.3 * self.ux, 0.3 * self.uy)]
        self.assertFalse(self.p.recentre_clear(out))

    def test_without_a_recentre_request_nothing_is_certified(self):
        p = FastConnectedPlanner(CLEARANCE, clearance_floor=CLEARANCE, occupied_radius=0.025)
        p.observe(*slalom(0.10))                 # beyond the slack
        p.plan(0.0)
        self.assertIsNone(p.recentre)
        self.assertFalse(p.recentre_clear([(0.0, 0.0), (0.0, -0.05)]))


class NoseMountedSidestepTests(unittest.TestCase):
    """The way out beside the body centre, seen from the nose lidar."""

    def setUp(self):
        self.p = mounted_planner(mounted_scan(*INSIDE[0], math.pi))
        self.assertEqual(self.p.plan(0.0), [])
        self.assertLess(float(self.p.distances([(0, 0)])[0]), CLEARANCE)
        self.ux, self.uy = self.p.recentre

    def along(self, metres):
        return [(0.0, 0.0)] + [(k * 0.005 * self.ux, k * 0.005 * self.uy)
                               for k in range(1, int(round(metres / 0.005)) + 1)]

    def test_a_4_cm_sidestep_inside_the_airframe_is_observed_and_certified(self):
        self.assertGreater(self.uy, 0.9, f'out to the body left, away from the block: {self.p.recentre}')
        step = self.along(0.04)
        self.assertTrue(self.p.known(step).all())
        self.assertTrue(self.p.recentre_clear(step))

    def test_blind_travel_beyond_the_airframe_stays_unobserved(self):
        self.assertFalse(self.p.known(self.along(0.12)).all())
        self.assertFalse(self.p.recentre_clear(self.along(0.12)))


class RecordedSlotRouteTests(unittest.TestCase):
    """Recorded scans where the committed planner hugged block 2 at 0.450-0.457 m."""

    def test_the_route_keeps_the_sampling_reserve(self):
        record = json.load(open(FIXTURE, encoding="utf-8"))
        self.assertEqual(record['mount_translation_xy'], list(MOUNT))
        for s in record['scans']:
            with self.subTest(run=s['run'], pose=s['pose']):
                raw = zlib.decompress(base64.b64decode(s['ranges']))
                mm = struct.unpack(f"<{len(raw) // 2}H", raw)
                scan = LaserScan()
                scan.angle_min, scan.angle_increment = s['angle_min'], s['angle_increment']
                scan.range_min, scan.range_max = s['range_min'], s['range_max']
                scan.ranges = [float('inf') if v == 0 else v / 1000.0 for v in mm]
                p = mounted_planner(scan)
                yaw = s['pose'][2]
                axis = math.atan2(math.sin(math.pi - yaw), math.cos(math.pi - yaw))   # west, body frame
                path = p.plan(axis)
                self.assertTrue(path, p.reason)
                self.assertGreaterEqual(route_clearance(p, path), CLEARANCE + SAMPLING_RESERVE - 1e-3)


class R12SlotTests(unittest.TestCase):
    """Controller side, closed loop on the r12 geometry."""

    fly = slalom_module.SlalomTraverseTests.fly

    @classmethod
    def setUpClass(cls):
        if not rclpy.ok():
            rclpy.init()

    @classmethod
    def tearDownClass(cls):
        if rclpy.ok():
            rclpy.shutdown()

    def setUp(self):
        self.node = VelocityController()
        self.node.set_parameters([Parameter('passage_half_width', value=CLEARANCE),
                                  Parameter('clearance_floor_m', value=CLEARANCE),
                                  Parameter('cruise_speed', value=1.0),
                                  Parameter('vel_command_delay_s', value=0.0),
                                  Parameter('motion_computation_budget_s', value=0.0)])
        self.node._planner.clearance = CLEARANCE
        self.sent = []
        self.node.pub_sp.publish = self.sent.append
        self.node.enabled = True
        self.node.state = "CRUISE"

    def tearDown(self):
        self.node.destroy_node()

    def through_r12(self, *args, **kwargs):
        saved = slalom_module.WALLS, slalom_module.BLOCKS
        slalom_module.WALLS, slalom_module.BLOCKS = R12_RECTS[:2], R12_RECTS[2:]
        try:
            # fly() fails on airframe contact or on not passing goal_x.
            return self.fly(*args, **kwargs)
        finally:
            slalom_module.WALLS, slalom_module.BLOCKS = saved

    def test_the_sidestep_command_is_published_not_zeroed(self):
        states, commands = [], []
        x, y = R12_STALL
        t = [0.0]
        self.node._now = lambda: t[0]
        for _ in range(6):
            pose = PoseStamped()
            pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = x, y, 1.2
            pose.pose.orientation.z, pose.pose.orientation.w = 1.0, 0.0     # heading west
            self.node._on_pose(pose)
            scan = scan_at(x, y, math.pi, R12_RECTS)
            scan.header.stamp.sec, scan.header.stamp.nanosec = int(t[0]), int((t[0] % 1) * 1e9)
            self.node._on_scan(scan)
            self.node._tick()
            states.append(self.node.state)
            commands.append((self.sent[-1].velocity.x, self.sent[-1].velocity.y))
            t[0] += 0.05
        self.assertIn('RECENTRE', states)
        moving = [c for s, c in zip(states, commands) if s == 'RECENTRE' and math.hypot(*c) > 0.05]
        self.assertTrue(moving, f'every recentre command was zeroed: {list(zip(states, commands))}; '
                                f'{self.node.last_detail}')
        # Heading west, body left (+y) is world south: away from the block.
        self.assertTrue(all(vy > 0 for _, vy in moving), moving)

    def test_r12_stall_point_is_flown_out_through_the_slot(self):
        _, closest, track = self.through_r12(*R12_STALL, math.pi, goal_x=8.0, max_t=60.0)
        self.assertGreaterEqual(closest, CLEARANCE - RECENTRE_SLACK, track[-10:])

    def test_from_inside_the_clearance_with_the_nose_lidar(self):
        for start in INSIDE:
            with self.subTest(start=start):
                self.tearDown()
                self.setUp()
                before = min(slalom_module.gap_to(*start, r) for r in R12_RECTS)
                _, closest, track = self.through_r12(*start, math.pi, goal_x=8.0, max_t=60.0,
                                                     mount=MOUNT, scan_delay_s=0.05, command_delay_s=0.1)
                self.assertGreaterEqual(closest, before - 1e-3, f'clearance only grows: {track[-10:]}')


if __name__ == "__main__":
    unittest.main()
