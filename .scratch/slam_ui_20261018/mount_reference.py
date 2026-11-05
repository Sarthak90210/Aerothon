"""Reference display projection from the production scan-mount quaternion."""
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from mission_bringup.scan_mount import mount_quaternion
from mission_bringup.scan_odometry import quaternion_matrix

rng = np.random.default_rng(20261018)
cases = []
for _ in range(80):
    mount = dict(geometry_measured=True, x_m=float(rng.uniform(-.3,.3)), y_m=float(rng.uniform(-.3,.3)),
                 z_m=.1, roll_deg=float(rng.uniform(-3,3)), pitch_deg=float(rng.uniform(-3,3)),
                 yaw_deg=float(rng.uniform(-180,180)))
    q = SimpleNamespace(**dict(zip(('x','y','z','w'),mount_quaternion(mount))))
    p = rng.uniform(-10,10,2)
    transformed = quaternion_matrix(q) @ np.array([*p,0]) + np.array([mount['x_m'],mount['y_m'],mount['z_m']])
    cases.append(dict(mount=mount,point=p.tolist(),expected=transformed[:2].tolist()))
Path(__file__).with_name('mount_reference.json').write_text(json.dumps(cases))
print('80 production quaternion reference cases generated')
