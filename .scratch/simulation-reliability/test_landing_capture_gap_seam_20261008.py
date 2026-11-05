"""Real descent must retain its visual correction across a brief capture gap."""
import sys
from pathlib import Path
from types import SimpleNamespace as NS
import py_trees
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from mission_bt.mission_tree import PrecisionDescent

class Mav:
 def __init__(self):
  self.at=(.6328112676908547,-.38812870976581115,8.3722311432605)
  self.home_marker_xy=(.36968553276409133,-.12494144993480921)
  self.qr_offset=NS(x=.04,y=-.04,z=1.);self.gotos=[]
 def pos(self):return self.at
 def yaw(self):return 0.
 def home_local_xy(self):return (0.,0.)
 def qr_visible(self):return self.qr_offset.z>0.
 def goto(self,*args):self.gotos.append(args)
 def log(self,*args,**kwargs):pass

def test_capture_gap_does_not_erase_recent_visual_landing_correction():
 mav=Mav();leaf=PrecisionDescent(mav,marker_m=3.1,hfov_rad=.851919)
 leaf.initialise();assert leaf.update() is py_trees.common.Status.RUNNING
 visual=mav.gotos[-1]
 mav.at=(.8467049288690549,-.02237823648439341,8.204483492775719)
 mav.qr_offset=NS(x=0.,y=0.,z=0.)
 assert leaf.update() is py_trees.common.Status.RUNNING
 assert mav.gotos[-1][2]<=mav.at[2],'one lost frame must not climb back to the start height'
 assert mav.gotos[-1][:2]==visual[:2],'retain the recent visual target during the existing grace period'
