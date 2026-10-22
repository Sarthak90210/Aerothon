"""The return alignment's camera retry looks DOWN for a board cut off at the bottom.

shipped_20kmh_r5: stood off 3.6 m from the return board at the 5 m look
height, every identified frame at BANNER (-20 deg) was cut off at the bottom
edge, and the retry pointed the camera LEVEL -- further away from the board --
before two empty yaw sweeps. Cut off at the bottom it now retries at
BANNER_DOWN (-45 deg); cut off at the top it still retries level.
"""
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import py_trees

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/aerothon_mission/mission_bt'))
from mission_bt.mission_tree import AlignToBanner  # noqa: E402


def stage_with(box):
    poses, logs = [], []
    mav = SimpleNamespace(
        outbound_banner_xy=(8.5, -0.5),
        camera_state=dict(requested='BANNER', settled=True, stale=False, actual_rad=math.radians(-20)),
        set_camera_pose=poses.append,
        log=lambda msg, warn=False: logs.append(msg),
        yaw=lambda: math.pi, pos=lambda: (17.1, -4.6, 5.0))
    stage = AlignToBanner.__new__(AlignToBanner)
    stage.mav, stage.hfov, stage.clock = mav, math.radians(48.8), lambda: 100.0
    stage.search_camera_pose = 'BANNER'
    stage.step_index = stage._relocations = 0
    stage._return_level_tried, stage._return_level_pending = False, None
    stage._return_retry_pose, stage._last_clip_down = 'FORWARD', False
    stage._hits = stage._samples = stage._clipped = 0
    stage._best_bearing, stage._best_area = None, 0.0
    stage._hold = lambda yaw: None
    stage._target_yaw = math.pi
    stage._raise_to_visible_return_board = lambda: False
    frame = dict(identified=True, bearing=0.0, pose=dict(yaw=math.pi), board_px=box,
                 image_wh=[960, 540], board_area_px=20000.0)
    stage._new_banner_samples = lambda: [frame, frame, frame]
    return stage, poses, logs


def test_a_board_cut_off_at_the_bottom_is_looked_for_45_deg_down():
    stage, poses, logs = stage_with([300, 400, 300, 140])      # bottom at 540
    assert stage._dwell() is py_trees.common.Status.RUNNING
    assert poses == ['BANNER_DOWN']
    assert stage._return_retry_pose == 'BANNER_DOWN'
    assert any('45 deg down' in m for m in logs)


def test_a_board_cut_off_at_the_top_still_retries_level():
    stage, poses, logs = stage_with([300, 0, 300, 140])        # top at 0
    assert stage._dwell() is py_trees.common.Status.RUNNING
    assert poses == ['FORWARD']
    assert any('level' in m for m in logs)
