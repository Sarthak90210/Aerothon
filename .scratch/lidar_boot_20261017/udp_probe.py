"""Read-only MAVLink heartbeat/parameter-list probe from the operator laptop."""
import collections
import json
from pathlib import Path
import socket
import struct
import sys
import time


def crc(data):
    c=0xffff
    for v in data:
        t=v^(c&255);t^=(t<<4)&255
        c=((c>>8)^(t<<8)^(t<<3)^(t>>4))&0xffff
    return c


sequence=0
def frame(message,payload,extra):
    global sequence
    head=bytes((len(payload),sequence%256,254,190,message));sequence+=1
    return b'\xfe'+head+payload+struct.pack('<H',crc(head+payload+bytes((extra,))))


sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.bind(('192.168.0.102',0));sock.settimeout(.2)
started=time.monotonic();end=started+(float(sys.argv[2]) if len(sys.argv)>2 else 15);last=0;counts=collections.Counter();heartbeats=[];buffer=b'';parameters=set();expected_params=None;bad_crc=0;retry_at=0;retry_index=0;retry_requests=0
while time.monotonic()<end:
    if time.monotonic()-last>1:
        sock.sendto(frame(0,struct.pack('<IBBBBB',0,6,8,0,4,3),50),('192.168.0.101',14550))
        if not parameters:sock.sendto(frame(21,b'\x01\x01',159),('192.168.0.101',14550))
        last=time.monotonic()
    if expected_params and time.monotonic()-started>25 and time.monotonic()>retry_at:
        missing=sorted(set(range(expected_params))-parameters)
        if not missing:break
        index=missing[retry_index%len(missing)];retry_index+=1
        sock.sendto(frame(20,struct.pack('<hBB16s',index,1,1,b''),214),('192.168.0.101',14550))
        retry_at=time.monotonic()+.15;retry_requests+=1
    try:packet,peer=sock.recvfrom(65536)
    except socket.timeout:continue
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
        extra={0:50,22:220}.get(message)
        if extra is not None and crc(buffer[1:head+n]+bytes((extra,)))!=int.from_bytes(buffer[head+n:head+n+2],'little'):
            bad_crc+=1;buffer=buffer[1:];continue
        counts[message]+=1
        if message==0 and sysid==1 and compid==1 and len(payload)>=7:
            heartbeats.append({'system':sysid,'component':compid,'armed':bool(payload[6]&128),'received_after_s':round(time.monotonic()-started,3)})
        if message==22 and sysid==1 and compid==1 and len(payload)>=8:
            parameters.add(struct.unpack_from('<H',payload,6)[0]);expected_params=struct.unpack_from('<H',payload,4)[0]
        buffer=buffer[size:]
sock.close()
result=dict(source='operator laptop UDP to Pi router, no GCS Connect',messages=dict(counts),
            heartbeats=heartbeats,unique_parameters=len(parameters),expected_parameters=expected_params,missing_parameter_indices=[] if not expected_params else sorted(set(range(expected_params))-parameters),retry_read_requests=retry_requests,invalid_known_crc=bad_crc,
            heartbeat_received=bool(heartbeats),disarmed=bool(heartbeats) and all(not h['armed'] for h in heartbeats))
out=Path(sys.argv[1] if len(sys.argv)>1 else '.scratch/lidar_boot_20261017/udp_before.json')
out.write_text(json.dumps(result,indent=2));print(json.dumps(result))
sys.exit(0 if heartbeats else 1)
