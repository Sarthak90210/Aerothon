#!/usr/bin/env python3
"""The skip-corridor mission (GCS "Mission, skip corridor", 31 Oct 2026).

After the start QR the aircraft climbs to 10 m, crosses over the entry
corridor (its recorded ends, when the GCS has them) into the delivery zone
and searches as usual; after the drop it climbs to 10 m, crosses over the
exit corridor and lands at home. These pin the tree's shape, that the full
mission is unchanged, and how the crossing stage flies its points.

    source /opt/ros/jazzy/setup.bash
    python3 -m pytest sim/test_skip_corridor.py -v
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import py_trees                                              # noqa: E402

import test_behavior_tree as tb                              # noqa: E402
from mission_bt.mission_tree import (                       # noqa: E402
    STATE_NAMES, HighTransit, build_root)

S = py_trees.common.Status

CORRIDOR_STAGES = {"OutboundGate", "DescendToCorridorAlt", "DuckUnderBoard",
                   "GateAdvance", "Corridor", "ReturnToCorridorMouth",
                   "ReturnGate", "DescendToReturnCorridor", "ReturnCorridor",
                   "BackToScanAlt", "BannerTargetReturn", "CameraBannerReturn"}


def mission_names(skip):
    t = tb.TestMissionBT()
    t.setUp()
    root = build_root(t.mav, t.node, t.defaults, skip_corridor=skip)
    mission = [c for c in root.children if c.name == "Mission"][0]
    return mission.children


class TreeShapeTests(unittest.TestCase):

    def test_skip_tree_flies_over_both_corridors_and_nothing_else_changes(self):
        names = [c.name for c in mission_names(skip=True)]
        self.assertFalse(CORRIDOR_STAGES & set(names), names)
        order = ["ScanStartQR", "ClimbToSkipAlt", "CameraNadirForSkip",
                 "SkipTransitSpeed", "OverEntryCorridor", "EnterDeliveryZone", "DeliverySearch",
                 "DropUnlessSkipped", "ClimbForReturn",
                 "CameraNadirForReturnTransit", "RestoreNavigationSpeed",
                 "OverExitCorridor", "BannerTargetHome", "GotoHome",
                 "DescendForLanding", "CameraNadirForLanding",
                 "PrecisionDescent", "Land"]
        self.assertEqual([n for n in names if n in order], order)
        full = [c.name for c in mission_names(skip=False)]
        # Take-off to the start QR is the full mission's, stage for stage.
        self.assertEqual(names[:names.index("ClimbToSkipAlt")],
                         full[:full.index("CameraForwardForCorridor")])

    def test_full_mission_still_flies_the_corridors(self):
        names = {c.name for c in mission_names(skip=False)}
        self.assertTrue({"OutboundGate", "Corridor", "ReturnCorridor"} <= names)
        self.assertFalse({"ClimbToSkipAlt", "OverEntryCorridor",
                          "OverExitCorridor"} & names)

    def test_every_skip_leaf_has_a_gcs_state_name(self):
        missing = [c.name for c in mission_names(skip=True)
                   if c.name not in STATE_NAMES]
        self.assertEqual(missing, [])

    def test_the_crossings_and_return_climb_are_at_10_m(self):
        stages = {c.name: c for c in mission_names(skip=True)}
        self.assertEqual(stages["ClimbToSkipAlt"].target_alt(), 10.0)
        self.assertEqual(stages["ClimbForReturn"].target_alt(), 10.0)
        self.assertEqual(stages["OverEntryCorridor"].alt, 10.0)
        self.assertEqual(stages["EnterDeliveryZone"].alt, 10.0)
        self.assertEqual(stages["OverExitCorridor"].alt, 10.0)
        self.assertEqual(stages["GotoHome"].alt, 10.0)
        # The crossing commands the navigation speed the return restores
        # (headless, 31 Oct: none was ever set and the return failed).
        self.assertEqual(stages["SkipTransitSpeed"].transit_alt, 10.0)
        self.assertEqual(stages["SkipTransitSpeed"].previous_speed(),
                         stages["SkipTransitSpeed"].ceiling)
        self.assertLessEqual(stages["ClimbToSkipAlt"].tol, 0.2)
        # Down to the landing's own start height before the precision descent.
        self.assertEqual(stages["DescendForLanding"].target_alt(),
                         stages["PrecisionDescent"].start_alt)
        self.assertLess(stages["PrecisionDescent"].start_alt, 10.0)


class FlyingMav(tb.MockMav):
    """goto() moves the aircraft straight to the commanded point."""

    def __init__(self):
        super().__init__()
        self.exclusions = []
        self.gotos = []
        self.pose.pose.position.z = 10.0

    def goto(self, x, y, z, yaw=0.0):
        self.gotos.append((x, y, z, yaw))
        self.pose.pose.position.x = x
        self.pose.pose.position.y = y
        self.pose.pose.position.z = z

    def hold_position(self):
        pass


class HighTransitTests(unittest.TestCase):

    def run_stage(self, stage, ticks=50):
        stage.initialise()
        for _ in range(ticks):
            status = stage.update()
            if status != S.RUNNING:
                return status
        return status

    def test_flies_the_recorded_ends_in_order_at_its_altitude(self):
        mav = FlyingMav()
        mav.entry_corridor_local = ((2.0, 1.0), (8.0, 3.0))
        stage = HighTransit("OverEntryCorridor", mav,
                            lambda: mav.entry_corridor_local, 10.0)
        self.assertEqual(self.run_stage(stage), S.SUCCESS)
        visited = [(round(x, 3), round(y, 3)) for x, y, _, _ in mav.gotos]
        self.assertIn((2.0, 1.0), visited)
        self.assertEqual(visited[-1], (8.0, 3.0))
        self.assertLess(visited.index((2.0, 1.0)), visited.index((8.0, 3.0)))
        self.assertTrue(all(math.isclose(z, 10.0) for _, _, z, _ in mav.gotos))

    def test_without_recorded_points_it_passes_at_once(self):
        mav = FlyingMav()
        mav.entry_corridor_local = None
        stage = HighTransit("OverEntryCorridor", mav,
                            lambda: mav.entry_corridor_local, 10.0)
        self.assertEqual(self.run_stage(stage), S.SUCCESS)
        self.assertEqual(mav.gotos, [])

    def test_holds_the_heading_it_started_with(self):
        mav = FlyingMav()
        mav.yaw = lambda: 1.25
        stage = HighTransit("OverExitCorridor", mav,
                            lambda: ((1.0, 0.0), (5.0, 0.0)), 10.0)
        self.assertEqual(self.run_stage(stage), S.SUCCESS)
        self.assertTrue(all(yaw == 1.25 for *_, yaw in mav.gotos))


if __name__ == "__main__":
    unittest.main()
