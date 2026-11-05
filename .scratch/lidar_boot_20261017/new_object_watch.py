"""Bearing (body frame, CCW from nose) of whatever appears against a background.

The first `background_s` seconds of /scan telemetry are the empty scene; after
that, once a second, print the bearing/range of the largest cluster of beams at
least 0.15 m nearer than the background median.
"""
import asyncio
import json
import math
import sys
import time

import aiohttp
import numpy as np


def ranges(scan):
    return np.array([np.nan if r is None else r for r in scan['ranges']], float)


async def main(seconds, background_s, out):
    background, rows = [], []
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect('http://192.168.0.101:8899/ws?map_encoding=rle', compress=15,
                                      max_msg_size=8 * 1024 * 1024, heartbeat=2) as ws:
            start = time.monotonic()
            last = 0.0
            base = None
            while time.monotonic() - start < seconds:
                try:
                    m = await asyncio.wait_for(ws.receive(), 1.)
                except asyncio.TimeoutError:
                    continue
                if m.type != aiohttp.WSMsgType.TEXT:
                    continue
                env = json.loads(m.data)
                if env.get('kind') != 'telemetry':
                    continue
                scan = env['data'].get('scan', {})
                if not scan.get('ranges'):
                    continue
                r = ranges(scan)
                if time.monotonic() - start < background_s:
                    background.append(r)
                    continue
                if base is None:
                    base = np.nanmedian(np.vstack(background), axis=0)
                    base = np.where(np.isnan(base), np.inf, base)
                    print(json.dumps({'background_scans': len(background)}), flush=True)
                if time.monotonic() - last < 1.0:
                    continue
                last = time.monotonic()
                near = (r > 0.06) & (r < 2.0) & (r < base - 0.15)
                idx = np.flatnonzero(near)
                row = {'t': round(time.time(), 1), 'beams': int(idx.size)}
                if idx.size >= 3:
                    # largest run of adjacent beams, wrapping at the seam
                    groups, current = [], [idx[0]]
                    for i in idx[1:]:
                        if i - current[-1] <= 2:
                            current.append(i)
                        else:
                            groups.append(current)
                            current = [i]
                    groups.append(current)
                    g = max(groups, key=len)
                    a = scan['angle_min'] + np.array(g) * scan['angle_step']
                    bearing = math.degrees(math.atan2(np.sin(a).mean(), np.cos(a).mean()))
                    row.update(bearing_deg=round(bearing, 1), range_m=round(float(np.nanmedian(r[g])), 2),
                               cluster_beams=len(g))
                rows.append(row)
                print(json.dumps(row), flush=True)
    with open(out, 'w') as f:
        json.dump(rows, f, indent=1)


asyncio.run(main(float(sys.argv[1]), float(sys.argv[2]), sys.argv[3]))
