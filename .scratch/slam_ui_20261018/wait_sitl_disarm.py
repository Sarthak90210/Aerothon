import json
import time
from urllib.request import urlopen

start = time.monotonic()
while time.monotonic()-start < 180:
    with urlopen('http://127.0.0.1:8897/api/state', timeout=5) as response:
        state = json.load(response)
    execution = state.get('execution') or {}
    if state.get('fresh') and state.get('can_disconnect') and execution.get('disarmed') is True:
        print(json.dumps({'confirmed_disarmed':True,'execution':execution}), flush=True)
        break
    time.sleep(1)
else:
    raise RuntimeError('No confirmed live disarm within180s; no next task started')
