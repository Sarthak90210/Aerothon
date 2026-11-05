"""Braking must validate the current streamed target, including temporary holds."""
from types import SimpleNamespace
from test_search_braking_20261007 import make_stage
from mission_bt.mav_commander import Mav

def wire_real_command(mav):
 commander=object.__new__(Mav);commander._sp=None
 mav.position_target_xy=lambda:Mav.position_target_xy(commander)
 return commander

def test_replaced_search_goal_does_not_interrupt_current_stationary_hold():
 stage,mav,_=make_stage();commander=wire_real_command(mav)
 Mav.goto(commander,*mav.pos(),mav.yaw())
 assert not stage._search_braking_gate.tick(stage)
 assert stage._search_braking_gate.hold is None

def test_current_unsafe_command_is_checked_even_when_cached_goal_is_safe():
 stage,mav,_=make_stage();commander=wire_real_command(mav)
 stage._streamed_search_goal=(0.,0.)
 Mav.goto(commander,30.,0.,10.)
 assert stage._search_braking_gate.tick(stage)
 assert mav.gotos[-1][:3]==mav.pos()
