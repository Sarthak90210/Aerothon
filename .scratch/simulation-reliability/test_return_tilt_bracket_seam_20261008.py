"""A real search leaf must bracket opposing crops without translating."""
import sys,math
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from test_return_clipped_framing import setup


def test_opposing_fresh_vertical_crops_use_an_intermediate_camera_angle():
    stage,mav,observation,now=setup();stage._look='FORWARD'
    mav.set_camera_pose('FORWARD');before=mav.pos()
    mav.camera_state=dict(actual_rad=0.,settled=True,stale=False)
    observation['board_px']=[432,399,445,320];observation['bearing']=.024
    for sequence in (1,2,3):
        now[0]=1.+sequence*.1
        observation.update(sequence=sequence,capture_stamp=now[0]);stage.update()
    assert stage.phase=='clipped_focus' and stage._look=='BANNER'
    mav.camera_state['actual_rad']=-math.radians(20)
    stage.update()
    # V23's same identified board leaves the opposite edge at this tilt.
    observation['board_px']=[494,0,424,326]
    for sequence in (4,5,6):
        now[0]=1.+sequence*.1
        observation.update(sequence=sequence,capture_stamp=now[0]);stage.update()
    assert stage._look not in ('BANNER','FORWARD'), 'search oscillates between two camera tilts that both crop the board'
    assert float(stage._look)==-10.
    assert mav.pos()==before and stage._cur_alt==before[2]
    assert stage._sighting() is None, 'clipped geometry still cannot accept the gate'
