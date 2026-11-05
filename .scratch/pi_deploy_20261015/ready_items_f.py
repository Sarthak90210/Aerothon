import asyncio, json, aiohttp
async def main():
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect('ws://192.168.0.102:8899/ws') as ws:
            for _ in range(400):
                m = await asyncio.wait_for(ws.receive(), 10)
                try: p = json.loads(m.data)
                except Exception: continue
                x = p.get('telemetry') or p.get('data') or p if isinstance(p, dict) else None
                if isinstance(x, dict) and 'safety' in x:
                    print(sorted(x.keys()))
                    r = x.get('readiness')
                    print(json.dumps(r)[:3000] if r is not None else json.dumps(x['safety'])[:3000])
                    print('fence', json.dumps(x.get('geofence_vertices'))[:300])
                    return
asyncio.run(main())
