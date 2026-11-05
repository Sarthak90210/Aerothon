import argparse
import asyncio
import json
from pathlib import Path
import time

import aiohttp


async def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--seconds',type=float,default=10)
    parser.add_argument('--no-compress',action='store_true')
    args=parser.parse_args();telemetry=None;grid=None;samples=0;map_count=0
    async with aiohttp.ClientSession() as session:
        async with session.get('http://192.168.0.101:8899/api/state') as r:host=await r.json()
        async with session.ws_connect('http://192.168.0.101:8899/ws?map_encoding=rle',max_msg_size=8*1024*1024,compress=0 if args.no_compress else 15,heartbeat=2) as ws:
            end=time.monotonic()+args.seconds
            while time.monotonic()<end:
                try:m=await asyncio.wait_for(ws.receive(),1.)
                except asyncio.TimeoutError:continue
                if m.type!=aiohttp.WSMsgType.TEXT:continue
                env=json.loads(m.data)
                if env.get('kind')=='telemetry':telemetry=env['data'];samples+=1
                elif env.get('kind')=='map':
                    grid=env['data'];map_count+=1
                    if grid.get('encoding')=='rle':
                        runs=grid['rle'];grid['data']=[v for i in range(0,len(runs),2) for v in [runs[i]]*runs[i+1]]
    t=telemetry or {}
    summary=dict(runtime=host.get('runtime'),profile=host.get('profile_id'),telemetry_messages=samples,map_messages=map_count,compressed=not args.no_compress,
                 fcu=t.get('safety',{}).get('fcu_connected'),armed=t.get('mission',{}).get('armed'),
                 scan_beams=len(t.get('scan',{}).get('ranges',[])),
                 valid_returns=sum(r is not None for r in t.get('scan',{}).get('ranges',[])),
                 sample_age_s=t.get('sample_age_s'),slam_status=t.get('slam_status'),gps=t.get('gps'),
                 readiness=t.get('safety',{}).get('ready_items'),
                 map_shape=None if grid is None else [grid['w'],grid['h']],
                 map_resolution=None if grid is None else grid['res'])
    Path(args.out).write_text(json.dumps(dict(summary=summary,telemetry=telemetry,grid=grid),indent=2))
    print(json.dumps(summary))


asyncio.run(main())
