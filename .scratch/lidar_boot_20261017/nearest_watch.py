"""Print the live nearest-return bearing (body frame, CCW from nose) once a second."""
import asyncio
import json
import sys
import time

import aiohttp


async def main(seconds, out):
    rows = []
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect('http://192.168.0.101:8899/ws?map_encoding=rle', compress=15,
                                      max_msg_size=8 * 1024 * 1024, heartbeat=2) as ws:
            end, last = time.monotonic() + seconds, 0.0
            while time.monotonic() < end:
                try:
                    m = await asyncio.wait_for(ws.receive(), 1.)
                except asyncio.TimeoutError:
                    continue
                if m.type != aiohttp.WSMsgType.TEXT:
                    continue
                env = json.loads(m.data)
                if env.get('kind') != 'telemetry' or time.monotonic() - last < 1.0:
                    continue
                last = time.monotonic()
                cal = env['data'].get('lidar_cal', {})
                row = dict(t=round(time.time(), 1), body=cal.get('body_nearest'), raw=cal.get('raw_nearest'))
                rows.append(row)
                print(json.dumps(row), flush=True)
    with open(out, 'w') as f:
        json.dump(rows, f, indent=1)


asyncio.run(main(float(sys.argv[1]), sys.argv[2]))
