#!/usr/bin/env python3
"""Message sizes and arrival gaps on the aggregator and web-host sockets."""
import asyncio, json, sys, time, zlib
import aiohttp

async def probe(url, seconds):
    stats = {}
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect(url, max_msg_size=64*1024*1024, compress=15) as ws:
            t0 = last = time.monotonic(); gaps = []
            while time.monotonic() - t0 < seconds:
                m = await ws.receive(timeout=10)
                now = time.monotonic()
                if m.type != aiohttp.WSMsgType.TEXT:
                    print('closed', m.type, m.data, m.extra); break
                gaps.append(now - last); last = now
                env = json.loads(m.data); k = env['kind']
                st = stats.setdefault(k, {'n': 0, 'max': 0, 'deflated_max': 0})
                st['n'] += 1; st['max'] = max(st['max'], len(m.data))
                st['deflated_max'] = max(st['deflated_max'], len(zlib.compress(m.data.encode(), 6)))
                if k == 'telemetry':
                    st['scan_bytes'] = len(json.dumps(env['data'].get('scan'))) + len(json.dumps(env['data'].get('lidar_cal')))
            print(url, json.dumps(stats), 'max gap %.3f s' % max(gaps))

asyncio.run(probe(sys.argv[1], float(sys.argv[2])))
