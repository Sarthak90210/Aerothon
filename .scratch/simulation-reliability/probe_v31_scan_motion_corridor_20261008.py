"""Recorded corridor entry under the scan-motion candidate, no added reserve."""
import json,rclpy
from test_v30_recorded_corridor_physics_20261008 import fly,root
rclpy.init()
try:result=fly(compute_s=.05)
finally:rclpy.shutdown()
(root/'logs/reliability_v31_scan_motion_corridor_probe_20261008.json').write_text(json.dumps(dict(result=result,qualification=False,limitation='recorded entry/error, regenerated lidar; no ROS callback arrival ordering'),indent=2))
print(json.dumps(dict(clearance_m=result['clearance'],progress_m=result['progress'],seconds=result['seconds'],contacts=result['contacts'])),flush=True)
assert result['clearance']>=.70 and result['progress']>10.3 and not result['contacts']
