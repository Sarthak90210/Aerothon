"""Delivered distinct frames and braking, rather than publication counts."""
import math
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/aerothon_mission/mission_bt'))
from mission_bt.detector_timing import DetectorTiming, search_speed


def sample(timing,capture,received):
    return timing.add(dict(capture_stamp=capture,processed_stamp=received),received)


def test_duplicate_frames_never_qualify_rate():
    t=DetectorTiming()
    for now in (1.1,1.2,1.3,1.4): sample(t,1.0,now)
    assert t.qualified(1.4) is None


def test_capture_age_wins_over_new_arrival():
    t=DetectorTiming()
    for capture in (.1,.2,.3,.4): sample(t,capture,capture+3)
    assert t.qualified(3.4) is None


def test_rate_uses_slower_delivery_span():
    t=DetectorTiming()
    for capture,received in zip((1,1.1,1.2,1.3),(1.1,1.3,1.5,1.7)):
        sample(t,capture,received)
    q=t.qualified(1.7)
    assert abs(q['hz']-5)<1e-6
    assert abs(q['latency_s']-.4)<1e-6


def test_missing_or_future_timestamps_are_unqualified():
    t=DetectorTiming()
    assert not t.add({},1)
    assert not t.add(dict(capture_stamp=2,processed_stamp=1),1)
    assert not sample(t,float('nan'),1)


def test_speed_accounts_for_confirmation_latency_and_braking():
    v=search_speed(2.6,1.5,2,.2,1.5)
    assert 0<v<.5
    assert v*(4/2+.2+.6)+v*v/(2*.5)<=2.6-1.5+1e-9
    assert search_speed(2.6,1.5,1,.2,1.5)<v
    assert search_speed(1,1.5,2,.2,1.5)==0


def test_search_waits_for_both_detectors_and_speed_ack():
    from mission_bt.mission_tree import LawnmowerSearch
    stage=LawnmowerSearch.__new__(LawnmowerSearch)
    records=[]
    future=SimpleNamespace(done=lambda:False)
    mav=SimpleNamespace(detector_timing={'qr':DetectorTiming(),'red':DetectorTiming()},
                        pub_search_timing=SimpleNamespace(publish=records.append),set_speed=lambda v:future)
    stage.mav=mav;stage.alt=10;stage._ahead_rad=.25;stage.clearance_m=1.5
    stage.search_speed_mps=1.5;stage._speed=None
    for name in ('qr','red'):
        for stamp in (.2,.4,.6,.8): sample(mav.detector_timing[name],stamp,stamp+.05)
    assert stage._qualified_pace(.9) is False
    assert stage._qualified_pace(.9) is False
    future.done=lambda:True;future.result=lambda:SimpleNamespace(success=True)
    assert stage._qualified_pace(.9) is True
    assert stage._qualified_pace(2) is False


def test_same_count_moved_zone_invalidates_commanded_segment():
    from test_leg_routing import FlyingMav
    from mission_bt.leg_router import LegRouter
    from mission_bt.search_planner import path_hits_exclusion
    mav=FlyingMav(exclusions=[(10,20,10,15)])
    router=LegRouter(clearance_m=1.5)
    router.fly(mav,30,0,5)
    assert mav.gotos[-1][:2]==(30,0)
    mav.exclusions=[(10,20,-5,5)]
    router.fly(mav,30,0,5)
    assert not path_hits_exclusion([mav.pos()[:2],mav.gotos[-1][:2]],1.5,mav.exclusions)


def test_drift_revalidates_cached_command():
    from test_leg_routing import FlyingMav
    from mission_bt.leg_router import LegRouter
    from mission_bt.search_planner import path_hits_exclusion
    mav=FlyingMav(at=(0,10,5),exclusions=[(10,20,-5,5)])
    router=LegRouter(clearance_m=1.5)
    router.fly(mav,30,10,5)
    mav._pos=(0,0,5)
    router.fly(mav,30,10,5)
    assert not path_hits_exclusion([mav.pos()[:2],mav.gotos[-1][:2]],1.5,mav.exclusions)


def test_blocked_route_cancels_the_previously_streamed_goal():
    from test_leg_routing import FlyingMav
    from mission_bt.leg_router import LegRouter,BLOCKED
    mav=FlyingMav(at=(2,0,5))
    mav.hold_position=lambda:mav.goto(*mav.pos())
    router=LegRouter()
    router.fly(mav,30,0,5)
    mav.exclusions=[(29,31,-2,2)]
    assert router.fly(mav,30,0,5)==BLOCKED
    assert mav.gotos[-1][:3]==mav.pos()


def test_stalled_heading_never_authorizes_camera_blind_travel():
    import math
    from mission_bt.mission_tree import LawnmowerSearch
    from test_fail_closed_stages import FakeMav
    stage=LawnmowerSearch.__new__(LawnmowerSearch)
    stage.mav=FakeMav();stage.alt=10;stage.turn_tol=.1;stage._turn_hold=None
    initial=stage.mav.pos()[:2]
    for _ in range(100):
        assert stage._turning(math.pi/2)
        assert stage.mav.gotos[-1][:2]==initial


def test_search_faces_the_detour_segment_before_moving():
    import math
    from mission_bt.mission_tree import LawnmowerSearch
    from test_leg_routing import RoutedMav
    mav=RoutedMav(exclusions=[(10,20,-5,5)],at=(0,0,10))
    stage=LawnmowerSearch(mav,(-5,40,-20,20),10,exclusions=lambda:mav.exclusions)
    stage.initialise();stage.wps=[(30,0)]
    endpoint=stage.router.target(mav,30,0,10)
    expected=math.atan2(endpoint[1],endpoint[0])
    assert abs(expected)>.1
    stage.update()
    assert mav.gotos[-1][:2]==(0,0)
    assert abs(mav.gotos[-1][3]-expected)<1e-6

def paced_stage(speed,rate):
 from mission_bt.mission_tree import LawnmowerSearch
 stage=LawnmowerSearch.__new__(LawnmowerSearch);calls=[]
 future=SimpleNamespace(done=lambda:True,result=lambda:SimpleNamespace(success=True))
 stage.mav=SimpleNamespace(detector_timing={name:SimpleNamespace(qualified=lambda now:dict(hz=rate,latency_s=.14,capture_stamp=now,samples=40)) for name in ('qr','red')},set_speed=lambda value:(calls.append(value) or future))
 stage.alt=10.;stage._ahead_rad=.25;stage.clearance_m=1.5;stage.search_speed_mps=1.5
 stage._speed=speed;stage._pace_future=None
 return stage,calls


def test_small_safe_rate_recovery_does_not_restart_speed_acknowledgement():
 stage,calls=paced_stage(.6,20.)
 assert stage._qualified_pace(1.) is True, 'a .05 m/s increase may keep the already acknowledged lower safe cap'
 assert calls==[] and stage._speed==.6


def test_lower_admitted_speed_is_requested_immediately_and_acknowledged():
 stage,calls=paced_stage(.65,17.)
 assert stage._qualified_pace(1.) is False
 assert len(calls)==1 and abs(calls[0]-.6)<1.e-8
 assert stage._qualified_pace(1.) is True


def test_larger_safe_increase_still_requires_acknowledgement():
 stage,calls=paced_stage(.5,20.)
 assert stage._qualified_pace(1.) is False
 assert len(calls)==1 and abs(calls[0]-.65)<1.e-8
 assert stage._qualified_pace(1.) is True


def test_measured_braking_raises_the_paced_cap_and_the_default_is_unchanged():
 stage,calls=paced_stage(None,15.)
 stage.alt=5.;stage._ahead_rad=.47
 assert stage._qualified_pace(1.) is False
 default=calls[-1]
 assert abs(default-search_speed(5.*math.tan(.47),1.5,15.,.14,1.5))<.05, 'no brake_mps2: the 0.5 m/s^2 model'
 stage,calls=paced_stage(None,15.)
 stage.alt=5.;stage._ahead_rad=.47;stage.brake_mps2=2.0
 stage._qualified_pace(1.)
 assert calls[-1]>default+.1


def test_the_braking_allowance_still_stops_short_of_the_clearance():
 for decel in (.5,1.,2.,3.):
  v=search_speed(2.6,1.5,15.,.05,9.,decel=decel)
  delay=4/15.+.05+.6
  assert v*delay+v*v/(2*decel)<=2.6-1.5+1e-9
 assert search_speed(2.6,1.5,15.,.05,9.,decel=0.)==0.


def test_a_simulation_speed_override_replaces_the_derived_pace_and_says_so():
 stage,calls=paced_stage(None,15.)
 logs=[]
 stage.mav.log=lambda msg,warn=False:logs.append((msg,warn))
 stage.speed_override_mps=5.56
 stage._qualified_pace(1.)
 assert abs(calls[-1]-5.56)<1e-9
 assert any('OVERRIDE' in m and w for m,w in logs)


def test_no_override_keeps_the_derived_pace():
 stage,calls=paced_stage(None,15.)
 stage._qualified_pace(1.)
 assert calls[-1]<1.5


def continuous_stage():
 stage,calls=paced_stage(None,15.)
 stage.mav.detector_timing={name:SimpleNamespace(qualified=lambda now:None) for name in ('qr','red')}
 stage.mav.log=lambda msg,warn=False:None
 stage.speed_override_mps=5.56
 return stage,calls


def test_a_continuous_sweep_never_holds_for_stale_detector_timing():
 """The user's order, 21 Oct: 20 km/h without stopping, braking only for a QR.
 Stale detectors held the derived pace; the override flies on."""
 stage,calls=continuous_stage()
 assert stage._qualified_pace(1.) is True
 assert stage._qualified_pace(2.) is True
 assert calls==[5.56], 'the fixed speed is commanded once, not re-requested every tick'


def test_the_derived_pace_still_holds_for_stale_detector_timing():
 stage,calls=continuous_stage()
 stage.speed_override_mps=0.0
 assert stage._qualified_pace(1.) is False and calls==[]


def test_a_refused_speed_command_is_sent_again_without_holding():
 stage,calls=continuous_stage()
 refused=SimpleNamespace(done=lambda:True,result=lambda:SimpleNamespace(success=False))
 stage.mav.set_speed=lambda value:(calls.append(value) or refused)
 assert stage._qualified_pace(1.) is True
 assert stage._qualified_pace(2.) is True
 assert calls==[5.56,5.56]


def test_a_continuous_sweep_turns_onto_the_next_lane_on_the_move():
 from mission_bt.mission_tree import LawnmowerSearch
 stage=LawnmowerSearch.__new__(LawnmowerSearch)
 gotos=[]
 stage.mav=SimpleNamespace(yaw=lambda:0.0,pos=lambda:(0.,0.,10.),goto=lambda *a:gotos.append(a))
 stage.alt=10.;stage.turn_tol=math.radians(30.);stage._turn_hold=None
 stage.speed_override_mps=5.56
 assert stage._turning(math.pi) is False and gotos==[]
 stage.speed_override_mps=0.0
 assert stage._turning(math.pi) is True and gotos, 'the derived pace still turns in place'


def test_a_continuous_sweep_does_not_brake_before_a_red_ground_replan():
 import py_trees
 from mission_bt.mission_tree import LawnmowerSearch
 stage=LawnmowerSearch.__new__(LawnmowerSearch)
 stage._search_braking_gate=SimpleNamespace(tick=lambda s:True)
 stage.speed_override_mps=0.0
 assert stage.update() is py_trees.common.Status.RUNNING, 'the derived pace brakes first'
 stage.speed_override_mps=5.56
 stage.plan=None;stage.mav=SimpleNamespace(abort_reason=None)
 assert stage.update() is py_trees.common.Status.FAILURE, 'past the gate: no plan here, so FAILURE proves it was skipped'
