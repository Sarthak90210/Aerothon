"""The flown tree must reach the camera's landing tracking height."""
from unittest.mock import MagicMock
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'sim'))
import test_fail_closed_stages as fixtures
from mission_bt.mission_tree import build_root

def test_actual_mission_landing_handover_reaches_the_tracking_height():
    params=dict(fixtures.BuiltTreeCarriesTheNewBehaviourTests.PARAMS,
                target_marker_m=3.1,camera_hfov=.851919,image_height_px=720)
    root=build_root(fixtures.FakeMav(),MagicMock(),params)
    stages=list(root.iterate())
    home=next(s for s in stages if type(s).__name__=='GotoHome')
    descent=next(s for s in stages if type(s).__name__=='PrecisionDescent')
    assert home.alt>=descent.start_alt
