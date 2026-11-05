#!/usr/bin/env bash
set -e
id
cat /etc/NetworkManager/NetworkManager.conf
find /etc/NetworkManager/conf.d /usr/lib/NetworkManager/conf.d -maxdepth 1 -type f -printf '%f\n' 2>/dev/null || true
nmcli --version
ls -l /etc/netplan /run/NetworkManager/system-connections /etc/NetworkManager/system-connections 2>/dev/null || true
docker ps --format 'container={{.Names}} image={{.Image}} status={{.Status}}'
docker image ls --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}' | head -6
systemctl status aerothon-gcs --no-pager --lines=5
ls -l /home/pi5/aerothon_ws/runtime_manifest.json /home/pi5/aerothon_ws/gcs/index.html
find /home/pi5/aerothon_ws -maxdepth 1 -type d -printf '%f\n'
python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/pi5/aerothon_ws')
if (root/'runtime_manifest.json').exists():
    d=json.loads((root/'runtime_manifest.json').read_text()); print('existing_manifest_files',len(d.get('files',{})))
print('boot_wifi_config_bytes',Path('/boot/firmware/network-config').stat().st_size)
PY
