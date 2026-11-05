import base64,hashlib,json,zlib,numpy as np
from load import *
lo,hi=90,180
mm=np.array([[0 if r is None or not np.isfinite(r) else int(round(r*1000)) for r in s['ranges']] for s in scans[lo:hi]],dtype='<u2')
s=scans[lo]; mt=mounts['base_scan']
out=dict(
  scope='Real RPLIDAR C1 scans from the 19 October 2026 manual POSHOLD flight on the Pi; '
        'mapping-odometry regression only. The aircraft drifted about 1.4 m forward around '
        'scans 20-35 of this slice while pitching between +3 and -6 degrees (FCU local position).',
  source='.scratch/pi_deploy_20261019/held_observation.jsonl scans %d-%d'%(lo,hi-1),
  source_sha256=hashlib.sha256(EV.read_bytes()).hexdigest(),
  frame=s['frame'],mount_parent=mt['parent'],mount_translation=mt['translation'],mount_rotation_xyzw=mt['rotation'],
  angle_min=s['angle_min'],angle_increment=s['angle_increment'],range_min=s['range_min'],range_max=s['range_max'],
  beams=mm.shape[1],stamps=[x['stamp'] for x in scans[lo:hi]],
  ranges_encoding='zlib-compressed little-endian uint16 millimetres, row per scan, 0 = no return',
  ranges=base64.b64encode(zlib.compress(mm.tobytes(),9)).decode())
p=ROOT/'sim/fixtures/lidar_held_poshold_drift_20261019.json'
p.write_text(json.dumps(out,indent=1)+'\n'); print(p.stat().st_size)
