"""Poll the Pi GCS execution state; log changes to the evidence dir. Read-only."""
import json, sys, time, urllib.request
out = sys.argv[1]; wait_start = float(sys.argv[2]); limit = float(sys.argv[3])
t0 = time.time(); last = None; started = False
log = open(out + '/pi_execution_states.log', 'a')
while time.time() - t0 < limit:
    try:
        d = json.loads(urllib.request.urlopen('http://192.168.0.103:8899/api/state', timeout=5).read())
        e = d.get('execution') or {}
        s = (d.get('runtime'), e.get('state'), e.get('stage'), e.get('task'), e.get('reason') or e.get('outcome'))
    except Exception as x:
        s = ('error', repr(x)[:80])
    if s != last:
        line = time.strftime('%H:%M:%S') + ' ' + json.dumps(s)
        print(line, flush=True); log.write(line + '\n'); log.flush(); last = s
    if len(s) > 2 and s[1]: started = True
    if not started and time.time() - t0 > wait_start:
        print('no start observed'); break
    if started and s[1] in ('Completed', 'Failed', 'Outcome unknown', 'Cancelled'):
        print('terminal'); break
    time.sleep(5)
