#!/usr/bin/env bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH"
python3 - <<'PY'
import sys,math
sys.path.insert(0,'sim')
from test_slalom_traverse import scan_at,WALLS,BLOCKS,rect
from avoidance.local_planner import LocalPlanner
import numpy as np
WALLS[:]=[rect(5,1.55,10.2,.1),rect(5,-1.55,10.2,.1)]
BLOCKS[:]=[rect(8,-.75,.35,1.5),rect(5.5,.75,.35,1.5),rect(3,-.75,.35,1.5)]
for yaw in (2.529,math.pi):
 s=scan_at(8.65,0.62,yaw,WALLS+BLOCKS)
 b=s.angle_min+np.arange(len(s.ranges))*s.angle_increment;r=np.array(s.ranges)
 mask=np.abs(b)<math.radians(150)
 p=LocalPlanner();p.observe(b[mask],r[mask]);path=p.plan(math.pi-yaw)
 print(yaw,p.reason,path,p.distances([[0,0]]))
PY