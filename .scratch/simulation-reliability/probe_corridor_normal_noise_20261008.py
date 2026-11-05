"""Vary only normal lidar realisations in the actual corridor/airframe loop."""
import json
from pathlib import Path
import rclpy
from test_recorded_corridor_physics_seam_20261008 import fly,root
results=[]
for seed in range(5,17):
    rclpy.init()
    try:r=fly(compute_s=.05,lidar_seed=seed)
    finally:rclpy.shutdown()
    r['lidar_seed']=seed;results.append(r)
    (root/'logs/reliability_corridor_normal_noise_probe_20261008.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(dict(seed=seed,clearance=r['clearance'],progress=r['progress'],seconds=r['seconds'])),flush=True)
    if r['clearance']<.70:break
print('Diagnostic only; no qualification claim',flush=True)
