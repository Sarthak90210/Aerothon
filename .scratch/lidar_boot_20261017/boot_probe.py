"""Read-only UDP and HTTP observer across a Pi reboot. No Connect request."""
import collections
import datetime
import json
from pathlib import Path
import socket
import struct
import threading
import time
import urllib.request

start=time.monotonic()
events=[]
stop=threading.Event()
def http_observer():
    previous=None
    while not stop.is_set():
        try:
            with urllib.request.urlopen('http://192.168.0.101:8899/api/state',timeout=.7) as r:
                state=json.load(r)
            current=(state['runtime'],state['fresh'],state['profile_id'],state['connection_error'])
        except Exception:
            current=('unreachable',False,None,None)
        if current!=previous:
            events.append({'after_s':round(time.monotonic()-start,3),'state':current})
            previous=current
        stop.wait(1)

def crc(data):
    c=0xffff
    for v in data:
        t=v^(c&255);t^=(t<<4)&255
        c=((c>>8)^(t<<8)^(t<<3)^(t>>4))&0xffff
    return c

thread=threading.Thread(target=http_observer);thread.start()
sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.bind(('192.168.0.102',0));sock.settimeout(.2)
heartbeats=[];buffer=b'';last=0;seq=0;counts=collections.Counter()
print('BOOT OBSERVER READY',flush=True)
while time.monotonic()-start<150:
    if time.monotonic()-last>1:
        payload=struct.pack('<IBBBBB',0,6,8,0,4,3)
        header=bytes((len(payload),seq%256,254,190,0));seq+=1
        sock.sendto(b'\xfe'+header+payload+struct.pack('<H',crc(header+payload+b'\x32')),('192.168.0.101',14550))
        last=time.monotonic()
    try:packet,peer=sock.recvfrom(65536)
    except (socket.timeout,ConnectionResetError):continue
    if peer[0]!='192.168.0.101':continue
    buffer+=packet
    while buffer:
        if buffer[0] not in (0xfe,0xfd):buffer=buffer[1:];continue
        if len(buffer)<12:break
        version=buffer[0];n=buffer[1];head=10 if version==0xfd else 6
        size=head+n+2+(13 if version==0xfd and buffer[2]&1 else 0)
        if len(buffer)<size:break
        message=int.from_bytes(buffer[7:10],'little') if version==0xfd else buffer[5]
        sysid,compid=(buffer[5],buffer[6]) if version==0xfd else (buffer[3],buffer[4])
        payload=buffer[head:head+n]
        if message==0:
            if crc(buffer[1:head+n]+b'\x32')!=int.from_bytes(buffer[head+n:head+n+2],'little'):
                buffer=buffer[1:];continue
            if sysid==1 and compid==1 and len(payload)>=7:
                heartbeats.append({'after_s':round(time.monotonic()-start,3),'armed':bool(payload[6]&128)})
        counts[message]+=1;buffer=buffer[size:]
stop.set();thread.join();sock.close()
result={'host_started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'method':'read-only UDP ground heartbeat plus HTTP state; no Connect or Start',
        'http_events':events,'fcu_heartbeats':heartbeats,'messages':dict(counts)}
Path('.scratch/lidar_boot_20261017/boot_observer.json').write_text(json.dumps(result,indent=2))
gaps=[{'before_s':a['after_s'],'after_s':b['after_s'],'gap_s':round(b['after_s']-a['after_s'],3)} for a,b in zip(heartbeats,heartbeats[1:]) if b['after_s']-a['after_s']>3]
print(json.dumps({'http_events':events,'heartbeat_count':len(heartbeats),'heartbeat_gaps':gaps,'all_disarmed':bool(heartbeats) and all(not h['armed'] for h in heartbeats)}))
