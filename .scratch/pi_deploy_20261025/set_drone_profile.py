"""Save the aircraft's auto-connect connection profile through the Pi GCS.

    python3 set_drone_profile.py http://<pi-ip>:8899

As on 23 Oct 2026 (receipt .scratch/pi_deploy_20261023): profile 'vehicle',
FC on UART0 /dev/ttyAMA0 at 115200, camera /dev/video0, RPLIDAR C1
/dev/ttyUSB0, SLAM on, autoconnect; winch now the Pi L298N (24 Oct). The web
host only accepts edits while no runtime is connected; saving an autoconnect
profile also selects it, so the router follows it and the runtime connects at
boot with no operator Connect.
"""
import json
import sys
import urllib.error
import urllib.request

host = sys.argv[1].rstrip('/')
profile = {
    "id": "vehicle", "name": "Drone (Pi UART0)", "vehicle": "drone",
    "transport": "serial", "device": "/dev/ttyAMA0", "baud": 115200,
    "system_id": 1, "component_id": 1,
    "camera_device": "/dev/video0", "lidar_port": "/dev/ttyUSB0",
    "slam": True, "winch_backend": "l298n", "autoconnect": True,
}
state = json.loads(urllib.request.urlopen(host + '/api/state', timeout=30).read())
print('runtime:', state.get('runtime'), '| editable:', state.get('can_edit_profiles'),
      '| profiles:', [p.get('id') for p in state.get('profiles', [])])
existing = next((p for p in state.get('profiles', []) if p.get('id') == 'vehicle'), None)
if existing:
    existing.update(profile)
    profile = existing
req = urllib.request.Request(host + '/api/profiles', data=json.dumps(profile).encode(),
                             headers={'Content-Type': 'application/json'}, method='POST')
try:
    saved = json.loads(urllib.request.urlopen(req, timeout=30).read())
except urllib.error.HTTPError as e:
    print('save refused:', e.code, e.read()[:400].decode(errors='replace'))
    raise SystemExit(1)
print('saved:', {k: saved.get(k) for k in ('id', 'device', 'baud', 'winch_backend', 'autoconnect', 'slam')})
