import asyncio, json, aiohttp
async def main():
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect('ws://127.0.0.1:8899/ws') as ws:
            for _ in range(400):
                m = await asyncio.wait_for(ws.receive(), 10)
                try: p = json.loads(m.data)
                except Exception: continue
                if not isinstance(p, dict): continue
                x = p.get('telemetry') or p.get('data') or p
                if isinstance(x, dict) and 'safety' in x:
                    a = x.get('sample_age_s') or {}
                    print(json.dumps({'ready': x['safety'].get('ready'), 'reasons': x['safety'].get('ready_reasons'),
                        'fcu': x['safety'].get('fcu_connected'), 'state_age': a.get('state'), 'readiness_age': a.get('readiness'),
                        'runtime_health': x.get('runtime_health'), 'mode': x['mission'].get('mode'),
                        'armed': x['mission'].get('armed'), 'mission_state': x['mission'].get('state'), 'execution': x.get('execution')}))
                    return
            print('no telemetry frame')
asyncio.run(main())
