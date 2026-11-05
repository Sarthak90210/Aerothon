import asyncio, json, aiohttp
async def main():
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect('ws://192.168.0.102:8899/ws') as ws:
            for _ in range(400):
                m = await asyncio.wait_for(ws.receive(), 10)
                try: p = json.loads(m.data)
                except Exception: continue
                x = (p.get('telemetry') or p.get('data') or p) if isinstance(p, dict) else None
                if isinstance(x, dict) and 'devices' in x:
                    print(json.dumps(x.get('devices'))[:1500]); print(json.dumps(x.get('detector_rates'))[:600]); return
asyncio.run(main())
