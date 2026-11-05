"""Reproduce horizontally clipped return lettering while actual yaw changes."""
import math,sys
from pathlib import Path
import pytest
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from test_return_capture_batching import turning_top_crop_stage

def test_actual_turning_return_width_clips_trigger_bounded_existing_backoff():
    leaf,mav,now,captures=turning_top_crop_stage();before=leaf._anchor
    for capture in captures:
        capture.update(identified=True,board_px=[0,402,1280,317],bearing=.029)
    captures.append(dict(captures[-1],sequence=5,capture_stamp=1.15,identified=False,board_px=None))
    leaf._settle()
    assert leaf._backoffs==1 and leaf.phase is leaf.RELOCATE
    theta=captures[3]['pose']['yaw']-math.atan(.029*math.tan(leaf.hfov/2))
    assert leaf._anchor[0]==pytest.approx(before[0]-leaf.backoff_m*math.cos(theta))
    assert leaf._anchor[1]==pytest.approx(before[1]-leaf.backoff_m*math.sin(theta))
    assert leaf._anchor[2]==before[2]
    assert leaf._good_vantage is None and leaf._sq_steps==0
