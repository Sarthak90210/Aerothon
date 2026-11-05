import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

url = 'http://127.0.0.1:8897'
with urlopen(url+'/api/state', timeout=5) as response:
    before = json.load(response)
assert before['fresh'] and before['can_disconnect'] and before['execution'].get('disarmed') is True
request = Request(url+'/api/disconnect', data=b'{}', headers={'Content-Type':'application/json'}, method='POST')
with urlopen(request, timeout=25) as response:
    after = json.load(response)
assert after['runtime'] == 'Stopped'
out = {'wall_time':time.time(), 'confirmed_disarm_before_disconnect':before,
       'disconnect_result':after, 'owned_simulator_pgid':13254, 'owned_web_pid':13307,
       'owned_runtime_pgid':14937, 'process_shutdown_verification':'pending'}
path = Path(__file__).resolve().parent/'local_shutdown.json'
path.write_text(json.dumps(out,indent=2))
print(json.dumps({'confirmed_disarmed':True,'runtime':after['runtime'],'receipt':str(path)}))
