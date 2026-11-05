import asyncio, json, aiohttp
async def main():
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect('ws://192.168.0.103:8899/ws') as ws:
            for _ in range(400):
                m = await asyncio.wait_for(ws.receive(), 10)
                try: p = json.loads(m.data)
                except Exception: continue
                x = (p.get('telemetry') or p.get('data') or p) if isinstance(p, dict) else None
                if isinstance(x, dict) and 'gimbal' in x:
                    print('gimbal', json.dumps(x.get('gimbal'))[:600]); print('mission', json.dumps(x.get('mission'))[:300]); return
asyncio.run(main())
