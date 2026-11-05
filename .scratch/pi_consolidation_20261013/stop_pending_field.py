"""Stop queued simulator repeats and request abort of the identified field run."""
import asyncio
import json
import os
from pathlib import Path
import signal
import time
import websockets

ROOT = Path(__file__).resolve().parents[2]
out = ROOT / 'logs/phase2_rendered_clarified_h115_ground_s20261004_field_p2r12'
config = json.loads((out / 'configuration.json').read_text())
assert config['ros_domain'] == 30 and config['conditions'] == 'field'
parent = 303
cmdline = Path(f'/proc/{parent}/cmdline').read_bytes().replace(b'\0', b' ').decode()
assert 'run_phase2_rendered_p2r12_20261013.sh' in cmdline
# A stopped parent cannot launch the next case; the active child keeps recording.
os.kill(parent, signal.SIGSTOP)

async def run():
    receipt = dict(run=str(out), reason='Already exceeded 900 s during outbound banner alignment; superseded by cleanup and final video request',
                   queued_parent_stopped=True, parent_pid=parent, requested_at_wall=time.time())
    async with websockets.connect('ws://127.0.0.1:8765', max_size=None) as ws:
        cid = 'cleanup-stop-field-20261013'
        await ws.send(json.dumps(dict(v=1, kind='command', data=dict(cmd='abort', cmd_id=cid, args={}))))
        end = time.monotonic() + 15
        while time.monotonic() < end:
            msg = json.loads(await asyncio.wait_for(ws.recv(), 10))
            if msg.get('kind') == 'ack' and msg.get('data', {}).get('cmd_id') == cid:
                receipt['ack'] = msg['data']
                break
    (Path(__file__).parent / 'interrupted_field_run.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=2))

asyncio.run(run())
