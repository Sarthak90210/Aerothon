"""A transient recorded scan-age miss must stop, then admit only fresh data."""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from test_gate_braking import actor
from mission_bt.gate_braking import RUNNING

def test_transient_capture_age_miss_holds_without_aborting_or_crossing():
    mav,leaf=actor();leaf._phase='CROSS';leaf._flight_distance=4.1
    mav.t=1.35;mav.observe();mav._scan.header.stamp.sec=1;mav._scan.header.stamp.nanosec=0
    # The V21 recorder measured 0.31-0.37 s lidar age while pose/velocity
    # remained fresh. No new crossing target is legal on that tick.
    assert leaf.update() is RUNNING
    assert mav.commands[-1]==mav.xyz
    assert leaf._t==0 and leaf._target==(16.,-15.)
    mav.t=1.55;mav.observe()
    leaf.router.fly=lambda vehicle,x,y,z,yaw:vehicle.goto(x,y,z,yaw)
    assert leaf.update() is RUNNING
    assert mav.commands[-1]==(16.,-15.,2.)
