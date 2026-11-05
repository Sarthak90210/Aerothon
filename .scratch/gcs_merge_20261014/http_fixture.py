"""Temporary HTTP-intranet command sink. No FCU, ROS or actuator connection."""
import asyncio
import json
import sys
import threading
import time
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / 'fixture_deps'))
import websockets

host = '192.168.0.100'
http = ThreadingHTTPServer((host, 8998), partial(SimpleHTTPRequestHandler, directory=str(ROOT / 'src/aerothon_gcs/tauri_app/dist')))
threading.Thread(target=http.serve_forever, daemon=True).start()
telemetry = dict(mission=dict(selected=None, state='FIXTURE_ONLY', armed=False, mode=''),
    flight=dict(x=None,y=None,alt=None),gps=dict(lat=None,lon=None,sats=None,fix='NO'),
    power=dict(volt=None,pct=None),nav=dict(front_m=None,centering_err=None,cmd_vx=None),
    percep=dict(start_qr='',target_match=False,banner=False,redzone_visible=False),
    safety=dict(ready=False,fcu_connected=False,ready_reasons=['Isolated HTTP contract fixture. No FCU connected.']),
    checklist={},sample_age_s={})

async def handler(ws):
    async def snapshots():
        while True:
            await ws.send(json.dumps(dict(v=1,kind='telemetry',t=time.time(),data=telemetry)))
            await asyncio.sleep(.2)
    task = asyncio.create_task(snapshots())
    try:
        async for raw in ws:
            e = json.loads(raw)
            d = e.get('data',{})
            accepted = e.get('kind') == 'command' and d.get('cmd') == 'set_target' and d.get('args',{}).get('target') == 'HTTP_CONTRACT_TEST'
            if accepted:
                (HERE/'http-command.json').write_text(json.dumps(dict(scope='isolated command sink, no hardware',request=e),indent=2))
            await ws.send(json.dumps(dict(v=1,kind='ack',t=time.time(),data=dict(cmd_id=d.get('cmd_id'),cmd=d.get('cmd'),result='accepted' if accepted else 'rejected',reason='Isolated test sink; no physical actuation.'))))
    finally:
        task.cancel()

async def main():
    async with websockets.serve(handler, host, 18766):
        print(f'Isolated HTTP fixture http://{host}:8998; WebSocket {host}:18766',flush=True)
        await asyncio.Future()
asyncio.run(main())
