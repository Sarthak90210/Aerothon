import asyncio, json, aiohttp
async def main():
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect('ws://192.168.0.102:8899/ws') as ws:
            for _ in range(400):
                m = await asyncio.wait_for(ws.receive(), 15)
                try: p = json.loads(m.data)
                except Exception: continue
                x = (p.get('telemetry') or p.get('data') or p) if isinstance(p, dict) else None
                if isinstance(x, dict) and 'safety' in x:
                    s_ = x['safety']
                    print('ready', s_.get('ready'))
                    for it in s_.get('ready_items', []):
                        print(' ', 'OK ' if it['ok'] else 'NO ', it['label'], '|', str(it['value'])[:50], '|', it['reason'][:80])
                    print('mission', json.dumps(x.get('mission'))[:250])
                    print('gps', json.dumps(x.get('gps'))[:200]); print('power', json.dumps(x.get('power'))[:200])
                    print('ages', json.dumps(x.get('sample_age_s'))[:300])
                    return
asyncio.run(main())
