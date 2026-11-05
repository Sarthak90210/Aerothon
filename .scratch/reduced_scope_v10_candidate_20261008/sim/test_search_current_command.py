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

def test_completed_margin_hold_hands_control_back_to_certified_router():
 stage,mav,now=make_stage();commander=wire_real_command(mav)
 original=mav.goto
 def goto(*args):
  original(*args);Mav.goto(commander,*args)
 mav.goto=goto
 mav._pos=(9.,0.,10.)
 Mav.goto(commander,30.,0.,10.)
 gate=stage._search_braking_gate
 assert gate.tick(stage)
 for stamp in (1.1,1.2,1.3):
  now[0]=stamp
  mav.delivery_inputs.update(pose_stamp=stamp,velocity_stamp=stamp,speed=.02)
  assert gate.tick(stage)
 assert gate.hold is None
 assert not gate.tick(stage), 'completed braking hold must allow a fresh certified escape'
 # The handoff does not exempt a replacement travel command.
 Mav.goto(commander,30.,0.,10.)
 assert gate.tick(stage)
 assert gate.hold is not None

def test_real_leaf_issues_safe_escape_after_completed_margin_braking():
 stage,mav,now=make_stage();commander=wire_real_command(mav)
 original=mav.goto
 def goto(*args):
  original(*args);Mav.goto(commander,*args)
 mav.goto=goto;mav._pos=(9.,0.,10.)
 Mav.goto(commander,30.,0.,10.)
 stage.update()
 for stamp in (1.1,1.2,1.3):
  now[0]=stamp;mav.delivery_inputs.update(pose_stamp=stamp,velocity_stamp=stamp,speed=.02)
  stage.update()
 stage.update()
 goal=mav.position_target_xy()
 assert goal != (9.,0.), 'leaf must command escape, not repeat the stationary hold'
 assert stage.router._segment_safe(mav,goal)
 assert not stage._search_braking_gate.tick(stage)

def test_completed_hold_does_not_release_after_motion_evidence_becomes_stale():
 stage,mav,now=make_stage();commander=wire_real_command(mav)
 original=mav.goto
 def goto(*args):
  original(*args);Mav.goto(commander,*args)
 mav.goto=goto;mav._pos=(9.,0.,10.)
 Mav.goto(commander,30.,0.,10.)
 gate=stage._search_braking_gate;assert gate.tick(stage)
 for stamp in (1.1,1.2,1.3):
  now[0]=stamp;mav.delivery_inputs.update(pose_stamp=stamp,velocity_stamp=stamp,speed=.02)
  assert gate.tick(stage)
 now[0]=2.
 assert gate.tick(stage)
 assert gate.hold is not None

def test_settled_braking_allows_turn_in_place_until_escape_heading_is_reached():
 stage,mav,now=make_stage();commander=wire_real_command(mav)
 original=mav.goto
 def goto(*args):
  original(*args);Mav.goto(commander,*args)
 mav.goto=goto;mav._pos=(9.,0.,10.);stage.crab=False
 stage._turn_hold=(9.05,0.);stage._turn_best=3.141592653589793;stage._turn_stall=0
 Mav.goto(commander,30.,0.,10.)
 stage.update()
 for stamp in (1.1,1.2,1.3):
  now[0]=stamp;mav.delivery_inputs.update(pose_stamp=stamp,velocity_stamp=stamp,speed=.02)
  stage.update()
 for _ in range(8):
  stage.update()
  assert stage._search_braking_gate.hold is None, 'a stationary turn must not restart braking'
  assert mav.position_target_xy()==mav.pos()[:2], 'old turn hold must not pull toward newly observed paint'
 stage._yaw=lambda target:0.
 stage.update()
 assert mav.position_target_xy()!=mav.pos()[:2]
 assert stage.router._segment_safe(mav,mav.position_target_xy())
