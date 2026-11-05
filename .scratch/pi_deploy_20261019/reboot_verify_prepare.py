"""Record software/Wi-Fi state, disconnect through the normal gate, then verify boot persistence."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

d=json.load(sys.stdin)
stage=Path('/home/pi5/aerothon-stage/20261019-slam-ui')
workspace=Path('/home/pi5/aerothon_ws')
manifest=json.loads((workspace/'runtime_manifest.json').read_text())
for name,digest in manifest['files'].items():
    assert hashlib.sha256((workspace/name).read_bytes()).hexdigest()==digest, name
software=(stage/'software_check.log').read_text()
assert 'FAIL ' not in software
state=json.load(urllib.request.urlopen('http://127.0.0.1:8899/api/state',timeout=8))
assert state['can_disconnect'], 'Live shutdown gate does not permit disconnect'
request=urllib.request.Request('http://127.0.0.1:8899/api/disconnect',data=b'{}',headers={'Content-Type':'application/json'},method='POST')
result=json.load(urllib.request.urlopen(request,timeout=30))
assert result['runtime']=='Stopped', result
subprocess.run(['systemctl','stop','aerothon-gcs.service'],check=True,timeout=70)
receipt=dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    payload_verified=len(manifest['files']),software_passes=software.count('PASS '),
    normal_disconnect=result['runtime'],wifi_profile_persistent=Path('/etc/NetworkManager/system-connections/iphone.nmconnection').is_file(),
    clock_before_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),clock_adjusted=False)
if abs(time.time()-d['epoch'])>300:
    subprocess.run(['timedatectl','set-ntp','false'],check=True)
    subprocess.run(['date','-u','-s','@'+str(d['epoch'])],check=True,capture_output=True)
    hwclock=shutil.which('hwclock')
    if hwclock:
        subprocess.run([hwclock,'--systohc'],check=False,capture_output=True)
    subprocess.run(['timedatectl','set-ntp','true'],check=True)
    receipt['clock_adjusted']=True
receipt['clock_after_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(stage/'pre_reboot.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
subprocess.run(['systemd-run','--unit=aerothon-verified-reboot-20261019','--on-active=4s','/usr/sbin/reboot'],check=True)
