#!/usr/bin/env bash
hostname
uname -m
cat /etc/os-release
uptime
findmnt -no SOURCE,FSTYPE /
df -h / /home/pi5/aerothon_ws
free -h
sudo -n true && echo SUDO_READY
ip -br address
ip route
for service in NetworkManager systemd-networkd wpa_supplicant aerothon-router aerothon-gcs docker; do
    printf '%s ' "$service"; systemctl is-active "$service" || true
done
command -v nmcli || true
command -v netplan || true
command -v iw || true
rfkill list 2>/dev/null || true
ls -l /etc/netplan /etc/NetworkManager/system-connections /boot/firmware/network-config 2>/dev/null || true
networkctl status wlan0 --no-pager 2>/dev/null | head -30 || true
if command -v nmcli >/dev/null; then
    nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status
    nmcli -t -f NAME,UUID,TYPE,DEVICE connection show
    nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY device wifi list ifname wlan0 --rescan no
fi
vcgencmd get_throttled 2>/dev/null || true
vcgencmd pmic_read_adc 2>/dev/null | sed -n '/EXT5V/p' || true
sudo -n docker ps --format 'container={{.Names}} image={{.Image}} status={{.Status}}'
sudo -n docker image ls --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}' | head -8
cat /home/pi5/aerothon-deploy/runtime.env 2>/dev/null
ls -l /dev/ttyAMA* /dev/ttyUSB* /dev/video* 2>/dev/null || true
python3 - <<'PY'
import json, urllib.request
try:
    d=json.load(urllib.request.urlopen('http://127.0.0.1:8899/api/state',timeout=4))
    print(json.dumps({k:d.get(k) for k in ('profile_id','runtime','fresh','can_disconnect','execution','connection_error')}))
except Exception as e:
    print(type(e).__name__+': '+str(e))
PY
