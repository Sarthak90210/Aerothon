import asyncio, json, aiohttp
async def main():
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect('ws://192.168.0.102:8899/ws') as ws:
            for _ in range(400):
                m = await asyncio.wait_for(ws.receive(), 10)
                try: p = json.loads(m.data)
                except Exception: continue
                if not isinstance(p, dict): continue
                x = p.get('telemetry') or p.get('data') or p
                if isinstance(x, dict) and 'safety' in x:
                    items = x.get('readiness') or x['safety'].get('items') or []
                    print(json.dumps({'ready': x['safety'].get('ready'), 'reasons': x['safety'].get('ready_reasons'),
                        'mode': x['mission'].get('mode'), 'armed': x['mission'].get('armed'),
                        'mission_state': x['mission'].get('state')}))
                    for it in (items if isinstance(items, list) else []):
                        if isinstance(it, dict):
                            print(' ', it.get('ok'), it.get('label') or it.get('key'), '|', str(it.get('value'))[:70], '|', (it.get('reason') or '')[:80])
                    return
            print('no telemetry frame')
asyncio.run(main())
