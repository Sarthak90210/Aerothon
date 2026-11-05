import asyncio
import json
import os
from pathlib import Path
import signal
import websockets

async def run():
    async with websockets.connect('ws://127.0.0.1:8765', max_size=None) as ws:
        cid = 'wire-map-superseded-video'
        await ws.send(json.dumps(dict(v=1, kind='command', data=dict(cmd='abort', cmd_id=cid, args={}))))
        while True:
            msg = json.loads(await asyncio.wait_for(ws.recv(), 10))
            if msg.get('kind') == 'ack' and msg.get('data', {}).get('cmd_id') == cid:
                print(json.dumps(msg['data']))
                break
    p = 7000
    c = Path(f'/proc/{p}/cmdline').read_bytes()
    assert b'pi_cleanup_hard_field_both_s20261004_20261013' in c
    os.kill(p, signal.SIGCONT)
    print('Resumed identified harness so it can record RTL, landing/disarm and close normally')

asyncio.run(run())
