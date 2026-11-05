"""Alignment consumes captured frames, not aliases of the latest detail."""
from types import SimpleNamespace
from mission_bt.banner_captures import BannerCaptures
from mission_bt.mav_commander import Mav
from test_return_inherited_tilt import prepare


def batch_stage():
 leaf,mav,_,now=prepare();mav._yaw=0.
 leaf.dwell_s=.3
 mav.camera_state=dict(requested='FORWARD',actual_rad=0.,settled=True,stale=False)
 captures=BannerCaptures();commander=object.__new__(Mav);commander.banner_captures=captures
 commander.node=SimpleNamespace(get_clock=lambda:SimpleNamespace(now=lambda:SimpleNamespace(nanoseconds=round(now[0]*1.e9))))
 mav.banner_observation=lambda:Mav.banner_observation(commander)
 mav.banner_observations=lambda:Mav.banner_observations(commander)
 mav.banner_identified=lambda:bool(mav.banner_observation() and mav.banner_observation()['identified'])
 mav.banner_bearing=lambda:BannerCaptures.bearing_at(mav.banner_observation(),mav.yaw(),leaf.hfov) or 0.
 mav.banner_clipped=True
 def deliver(sequence,identified):
  stamp=1.+sequence*.02
  assert captures.pose(stamp,mav.pos(),mav.yaw())
  assert captures.receive(dict(capture_stamp=stamp,processed_stamp=stamp+.01,identified=identified,bearing=.2,
   board_px=[80,430,1199,289] if identified else None,board_area_px=346511 if identified else 0.,image_wh=[1280,720]),now[0])
 return leaf,mav,now,deliver


def test_clipped_frames_between_leaf_ticks_trigger_existing_bounded_backoff():
 leaf,mav,now,deliver=batch_stage();before=leaf._anchor
 now[0]=1.2
 for seq in range(1,7):deliver(seq,seq<=4)
 leaf._dwell()
 assert leaf._samples==6 and leaf._hits==4 and leaf._clipped==4, 'fresh captured lettering cannot disappear behind a newer negative frame'
 now[0]=1.4
 for seq in range(7,13):deliver(seq,False)
 leaf._dwell()
 assert leaf._samples==12 and leaf._hits==4 and leaf._clipped==4
 assert leaf._backoffs==1 and leaf.phase==leaf.RELOCATE
 assert leaf._anchor==(before[0]-leaf.backoff_m,before[1],before[2])
 assert leaf._good_vantage is None, 'clipped framing evidence may not accept a range or gate crossing'


def test_replayed_capture_history_does_not_inflate_the_sample_count():
 leaf,mav,now,deliver=batch_stage();now[0]=1.2;leaf.dwell_s=5.
 for seq in range(1,7):deliver(seq,False)
 leaf._dwell();first=leaf._samples
 for _ in range(4):leaf._dwell()
 assert first==6 and leaf._samples==first


def test_capture_history_before_new_dwell_epoch_is_not_counted():
 leaf,mav,now,deliver=batch_stage();now[0]=1.2
 for seq in range(1,7):deliver(seq,True)
 leaf._enter(leaf.DWELL);leaf._dwell()
 assert leaf._samples==0 and leaf._hits==0
