"""Restore one persistent NetworkManager Wi-Fi profile; secret arrives on stdin."""
import configparser
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import uuid

d=json.load(sys.stdin)
ssid=d['ssid']
secret=d['wifi_password']
if not 8 <= len(secret) <= 63:
    raise ValueError('WPA passphrase length is invalid')
backup=Path('/home/pi5/aerothon-backups/20261019-slam-ui/network')
backup.mkdir(parents=True,exist_ok=False)
os.chmod(backup.parent,0o700)
os.chmod(backup,0o700)
with tarfile.open(backup/'network_before.tar.gz','w:gz') as archive:
    for name in ('/etc/NetworkManager','/etc/netplan','/boot/firmware/network-config'):
        p=Path(name)
        if p.exists(): archive.add(p,arcname=str(p).lstrip('/'))
os.chmod(backup/'network_before.tar.gz',0o600)
profile=Path('/etc/NetworkManager/system-connections/iphone.nmconnection')
if profile.exists():
    raise RuntimeError('Profile path already exists; inspect it before replacing')
identifier=str(uuid.uuid4())
config=configparser.ConfigParser(interpolation=None)
config['connection']={'id':ssid,'uuid':identifier,'type':'wifi','interface-name':'wlan0','autoconnect':'true','autoconnect-priority':'100'}
config['wifi']={'mode':'infrastructure','ssid':ssid,'powersave':'2'}
config['wifi-security']={'key-mgmt':'wpa-psk','psk':secret}
config['ipv4']={'method':'auto','route-metric':'600'}
config['ipv6']={'method':'auto','route-metric':'600'}
config['proxy']={}
fd=os.open(profile,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as output:
    config.write(output,space_around_delimiters=False)
    output.flush(); os.fsync(output.fileno())
def run(args):
    result=subprocess.run(args,text=True,capture_output=True,timeout=40)
    print(result.stdout.replace(secret,'<REDACTED>').strip())
    if result.returncode:
        print(result.stderr.replace(secret,'<REDACTED>').strip())
        raise RuntimeError('NetworkManager command failed')
run(['nmcli','connection','load',str(profile)])
run(['nmcli','radio','wifi','on'])
run(['nmcli','--wait','30','connection','up','uuid',identifier])
run(['nmcli','-t','-f','GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS,IP4.GATEWAY','device','show','wlan0'])
print(json.dumps({'ssid':ssid,'uuid':identifier,'profile':str(profile),'backup':str(backup/'network_before.tar.gz'),
                  'persistent':True,'autoconnect':True,'file_mode':oct(profile.stat().st_mode&0o777),'ethernet_profile_changed':False}))
