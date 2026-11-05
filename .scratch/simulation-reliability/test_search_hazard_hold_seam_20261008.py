"""New red observations must invalidate a latched stationary search anchor."""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from mission_bt.mission_tree import LawnmowerSearch
from test_leg_routing import RoutedMav

def test_braking_anchor_inside_new_exclusion_must_take_certified_escape():
 mav=RoutedMav(at=(49.20995036686573,-18.33730770584774,9.878185873982721))
 now=273.1;mav.delivery_inputs=dict(pose_stamp=273.,velocity_stamp=273.,speed=.134)
 stage=LawnmowerSearch(mav,(17.,57.,-21.,10.),10.,exclusions=lambda:mav.exclusions,clock=lambda:now)
 stage.initialise();gate=stage._search_braking_gate
 anchor=(49.32662271657171,-18.223619929631525,10.,0.)
 gate.hold=anchor;gate.brake_started_stamp=270.
 mav.exclusions=[(47.,50.,-19.,-16.)]
 assert gate.tick(stage)
 assert mav.gotos[-1][:2]!=anchor[:2],'a newly unsafe stationary anchor cannot stay exempt from route checks'
 assert stage.router._segment_safe(mav,mav.gotos[-1][:2],exclusions=mav.exclusions)
 assert gate.completed_hold is None
