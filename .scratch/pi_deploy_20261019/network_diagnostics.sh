#!/usr/bin/env bash
ls -l /etc/resolv.conf
cat /etc/resolv.conf
cat /run/NetworkManager/resolv.conf 2>/dev/null || true
ip -4 route
ping -I wlan0 -c 2 -W 2 1.1.1.1 || true
python3 - <<'PY'
import json, socket, struct
name='www.raspberrypi.com'
packet=struct.pack('!HHHHHH',0x3217,0x100,1,0,0,0)+b''.join(bytes([len(p)])+p.encode() for p in name.split('.'))+b'\0'+struct.pack('!HH',1,1)
for server in ['192.168.0.1','1.1.1.1','8.8.8.8']:
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,b'wlan0\0')
    s.settimeout(2)
    try:
        s.sendto(packet,(server,53)); response,_=s.recvfrom(4096)
        header=struct.unpack('!HHHHHH',response[:12]); print(json.dumps({'dns_server':server,'via':'wlan0','rcode':header[1]&15,'answers':header[3]}))
    except Exception as e: print(json.dumps({'dns_server':server,'via':'wlan0','error':type(e).__name__}))
    finally: s.close()
s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,b'wlan0\0'); s.settimeout(3)
try:
    s.connect(('1.1.1.1',443)); print('WIFI_PUBLIC_TCP_OK')
except Exception as e: print('WIFI_PUBLIC_TCP_'+type(e).__name__)
finally: s.close()
PY
