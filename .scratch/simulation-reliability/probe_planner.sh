#!/usr/bin/env bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH"
python3 - <<'PY'
import sys,math
sys.path.insert(0,'sim')
from test_slalom_traverse import scan_at,WALLS,BLOCKS
from avoidance.local_planner import LocalPlanner
import numpy as np
for yaw in (math.pi,math.pi-.5,math.pi+.5):
 s=scan_at(7.56,-3.58,yaw,WALLS+BLOCKS)
 b=s.angle_min+np.arange(len(s.ranges))*s.angle_increment;r=np.array(s.ranges)
 mask=np.abs(b)<math.radians(150)
 p=LocalPlanner();p.observe(b[mask],r[mask]);path=p.plan(math.pi-yaw)
 print(yaw,p.reason,path,p.distances([[0,0]]))
PY