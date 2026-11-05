"""Clipped identity cannot cancel the framing backoff it just requested."""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from test_return_turning_width_crop import stage


def test_actual_width_recovery_transit_continues_until_a_complete_view():
    leaf,mav,now,captures=stage();leaf._settle()
    assert leaf._backoffs==1 and leaf.phase is leaf.RELOCATE
    target=leaf._anchor;position=mav.pos()
    captures[-1].update(identified=True,board_px=[0,402,1280,317])
    leaf._transit()
    assert leaf.phase is leaf.RELOCATE, 'clipped identity cancelled the required backoff before movement'
    assert leaf._anchor==target and mav.pos()==position
    assert mav.gotos[-1][:3]==target
    assert leaf._good_vantage is None
