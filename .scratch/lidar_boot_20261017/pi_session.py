"""Ephemeral SSH session, pinned to the user-confirmed rebuilt Pi host key."""
import base64
import getpass
import hashlib
import json
import shlex
import sys
import time

import paramiko


class ConfirmedPiKey(paramiko.MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        fingerprint='SHA256:'+base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip('=')
        if fingerprint!='SHA256:hb9hOhkoDKLFU5a0JPLTc6sa8r/FhocTUnpxkMzWYXw':
            raise paramiko.SSHException('Pi host identity differs from the user-confirmed key')


ssh=paramiko.SSHClient()
ssh.set_missing_host_key_policy(ConfirmedPiKey())
password=getpass.getpass('Pi password: ')
ssh.connect('192.168.0.101',username='pi5',password=password,look_for_keys=False,
            allow_agent=False,timeout=15,banner_timeout=20,auth_timeout=15)
ssh.get_transport().set_keepalive(5)
print('CONNECTED to confirmed Pi',flush=True)
for line in sys.stdin:
    try:
        request=json.loads(line)
        if request.get('exit'):
            break
        if 'put' in request:
            with ssh.open_sftp() as sftp:sftp.put(request['put'],request['remote'])
            print('UPLOAD COMPLETE',flush=True)
            continue
        if 'get' in request:
            with ssh.open_sftp() as sftp:sftp.get(request['get'],request['local'])
            print('DOWNLOAD COMPLETE',flush=True)
            continue
        command=request['cmd']
        if request.get('sudo'):
            command='sudo -S -p "" -- /bin/bash -c '+shlex.quote(command)
        inp,out,err=ssh.exec_command(command,timeout=request.get('timeout',60))
        if request.get('sudo'):
            inp.write(password+'\n');inp.flush()
        channel=out.channel
        while not channel.exit_status_ready() or channel.recv_ready() or channel.recv_stderr_ready():
            if channel.recv_ready():sys.stdout.write(channel.recv(65536).decode(errors='replace'));sys.stdout.flush()
            if channel.recv_stderr_ready():sys.stdout.write(channel.recv_stderr(65536).decode(errors='replace'));sys.stdout.flush()
            time.sleep(.05)
        print('\nEXIT',channel.recv_exit_status(),flush=True)
    except Exception as exc:
        print(type(exc).__name__+': '+str(exc),flush=True)
ssh.close()
