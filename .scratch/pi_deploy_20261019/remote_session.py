"""Task-local SSH session. Credentials stay in memory and never enter command lines."""
import base64
import getpass
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
import time
import paramiko

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
HOST = sys.argv[1] if len(sys.argv) > 1 else '192.168.0.104'
if HOST not in {'192.168.0.103','192.168.0.104'}:
    raise ValueError('Use a previously identified Pi address')
known = paramiko.HostKeys()
for path in [Path.home()/'.ssh'/'known_hosts', *sorted((ROOT/'.scratch').glob('pi_deploy_*/known_hosts'))]:
    if path.is_file():
        try:
            known.load(str(path))
        except (OSError, paramiko.SSHException):
            pass
probe = paramiko.Transport((HOST,22))
probe.start_client(timeout=12)
key = probe.get_remote_server_key()
fingerprint = 'SHA256:' + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip('=')
probe.close()
expected = known.lookup(HOST)
pinned_pi = known.lookup('192.168.0.104')
matches_pinned_pi = pinned_pi and any(k == key for k in pinned_pi.values())
if not matches_pinned_pi and (not expected or not any(k == key for k in expected.values())):
    print(json.dumps({'error':'host key changed', 'host':HOST,'fingerprint':fingerprint}),flush=True)
    raise SystemExit(3)
known.add(HOST,key.get_name(),key)
known.save(str(HERE/'known_hosts'))
print(json.dumps({'host':HOST,'host_key':fingerprint,'known_key':bool(expected),'matches_pinned_pi':bool(matches_pinned_pi)}),flush=True)
password = getpass.getpass('SSH password: ')
client = paramiko.SSHClient()
client.load_host_keys(str(HERE/'known_hosts'))
client.set_missing_host_key_policy(paramiko.RejectPolicy())
client.connect(HOST,username='pi5',password=password,look_for_keys=False,allow_agent=False,timeout=15)
client.get_transport().set_keepalive(15)
wifi_password = None
print('SSH_READY',flush=True)

def run(command,timeout=60,input_text=None,output_file=None,sudo=False):
    if sudo:
        command="sudo -S -p '' -- " + command
        input_text=password+'\n'+(input_text or '')
    stdin,stdout,stderr=client.exec_command(command,timeout=timeout)
    if input_text is not None:
        stdin.write(input_text)
        stdin.flush()
    stdin.channel.shutdown_write()
    chunks=[]
    deadline=time.monotonic()+timeout
    channel=stdout.channel
    while True:
        while channel.recv_ready(): chunks.append(channel.recv(65536).decode('utf-8','replace'))
        while channel.recv_stderr_ready(): chunks.append(channel.recv_stderr(65536).decode('utf-8','replace'))
        if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready(): break
        if time.monotonic()>deadline:
            channel.close()
            raise TimeoutError('Remote command exceeded its bounded timeout')
        time.sleep(.03)
    code=channel.recv_exit_status()
    output=''.join(chunks)
    if wifi_password: output=output.replace(wifi_password,'<REDACTED>')
    if output_file: (HERE/output_file).write_text(output,encoding='utf-8')
    return {'exit_code':code,'output':output}

for line in sys.stdin:
    try:
        request=json.loads(line)
        action=request.get('action','exec')
        if action=='close': break
        if action=='wifi_secret':
            wifi_password=getpass.getpass('Wi-Fi password: ')
            result={'wifi_secret_loaded':True}
        elif action=='exec':
            result=run(request['command'],request.get('timeout',60),output_file=request.get('output_file'),sudo=request.get('sudo',False))
        elif action=='run_file':
            path=Path(request['path'])
            if not path.is_absolute(): path=ROOT/path
            result=run('bash -s',request.get('timeout',60),path.read_text(),request.get('output_file'),request.get('sudo',False))
        elif action=='python_file':
            path=Path(request['path'])
            if not path.is_absolute(): path=ROOT/path
            script=path.read_text()
            payload=dict(request.get('data',{}))
            if request.get('wifi_secret'): payload['wifi_password']=wifi_password
            command='python3 -c '+shlex.quote(script)
            result=run(command,request.get('timeout',60),json.dumps(payload),request.get('output_file'),request.get('sudo',False))
        elif action in ('put','get'):
            sftp=client.open_sftp()
            try:
                if action=='put': sftp.put(str(ROOT/request['local']),request['remote'])
                else: sftp.get(request['remote'],str(HERE/request['local']))
            finally: sftp.close()
            result={'transferred':True}
        else: raise ValueError('Unknown action')
        print(json.dumps(result),flush=True)
    except Exception as error:
        print(json.dumps({'error':type(error).__name__,'message':str(error)}),flush=True)
client.close()
