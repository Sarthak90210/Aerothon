import sys, time, json, math
sys.path[:0] = ['/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/src/aerothon_gcs/gcs_aggregator']
import numpy as np
from gcs_aggregator.aggregator import max_pool_grid, pack_grid, _finite_json
rng = np.random.default_rng(0)
for w, h in ((800, 600), (2000, 2000)):
    g = np.full((h, w), -1, np.int8); g[: h*3//4, : w*3//4] = 0
    g[rng.random((h, w)) < 0.02] = 100
    data = g.ravel().tolist()
    t = time.perf_counter()
    step = max(1, math.ceil(max(w, h) / 1024)); ow, oh, out = max_pool_grid(data, w, h, step)
    t1 = time.perf_counter(); packed = pack_grid(out); t2 = time.perf_counter()
    env = json.dumps({'data': _finite_json({'w': ow, 'h': oh, **packed})}, separators=(',', ':')); t3 = time.perf_counter()
    print(w, h, 'pool %.3f pack %.3f json %.3f size %d KB' % (t1-t, t2-t1, t3-t2, len(env)//1024))
