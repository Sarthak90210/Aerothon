"""Read live telemetry without sending an operator command."""
import asyncio
import json
import time

import websockets


async def capture():
    samples = []
    async with websockets.connect('ws://127.0.0.1:8765', open_timeout=15) as client:
        deadline = time.monotonic() + 20
        while len(samples) < 5 and time.monotonic() < deadline:
            envelope = json.loads(await asyncio.wait_for(client.recv(), timeout=10))
            if envelope.get('kind') == 'telemetry':
                samples.append(envelope)
    assert len(samples) == 5
    state = samples[-1]['data']
    assert not state['mission'].get('armed'), 'Deployment check requires disarmed telemetry'
    assert state['mission'].get('state', 'idle').upper() in ('IDLE', 'WAITING', '')
    print(json.dumps(dict(received_frames=len(samples), first_timestamp=samples[0]['t'],
                          last_timestamp=samples[-1]['t'], operator_commands_sent=0,
                          telemetry=state), indent=2))


asyncio.run(capture())
