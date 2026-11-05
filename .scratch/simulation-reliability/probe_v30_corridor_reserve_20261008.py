"""Compare one reserve variable in the recorded return-entry airframe seam."""
import json,rclpy
from pathlib import Path
from test_v30_recorded_corridor_physics_20261008 import fly,root
results=[]
for reserve in (0.,.05):
 rclpy.init()
 try:result=fly(reserve=reserve,compute_s=.05)
 finally:rclpy.shutdown()
 results.append(result)
 print(json.dumps(dict(reserve_m=reserve,clearance_m=result['clearance'],progress_m=result['progress'],seconds=result['seconds'],contacts=result['contacts'])),flush=True)
(root/'logs/reliability_v30_corridor_reserve_probe_20261008.json').write_text(json.dumps(dict(results=results,qualification=False,limitation='recorded entry/error, regenerated lidar; no ROS callback arrival ordering'),indent=2))
assert results[-1]['clearance']>=.70
assert results[-1]['progress']>10.3 and not results[-1]['contacts']
