import json
from pathlib import Path
import subprocess
import time

here = Path(__file__).resolve().parent
path = here/'local_shutdown.json'
data = json.loads(path.read_text())
rows = subprocess.check_output(['ps','-eo','pid,ppid,pgid,args'], text=True).splitlines()
owned = []
for row in rows[1:]:
    parts = row.split(None,3)
    if len(parts) == 4 and (int(parts[0]) == 13307 or int(parts[2]) in (13254,14937)):
        owned.append(row)
assert not owned, owned
data['process_shutdown_verification'] = {'wall_time':time.time(),
    'owned_processes_remaining':owned, 'verified_groups':[13254,14937],
    'verified_web_pid':13307, 'physical_hardware_accessed':False}
path.write_text(json.dumps(data,indent=2))
subprocess.run(['/usr/bin/python3',str(here/'summarize_local.py')],check=True)
receipt = json.loads((here/'local_testing.json').read_text())
for item in receipt['commands']:
    req, res = item['request'], item['result']
    if req.get('cmd') == 'start':
        print(json.dumps({'task':req.get('args'), 'result':res}))
