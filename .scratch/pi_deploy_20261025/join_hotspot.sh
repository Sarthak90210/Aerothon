#!/usr/bin/env bash
# Join the iPhone hotspot for the setup downloads (run as root by the operator):
#   sudo bash ~/join_hotspot.sh
# Finds the hotspot by name (iPhones use a curly apostrophe), joins it with
# nmcli --ask so the operator types the Wi-Fi password, and makes it the
# Internet route (metric 50) while Ethernet keeps the router LAN for SSH.
# Revert after setup: nmcli con modify <name> connection.autoconnect-priority -10
# (piwifi, the GCS network, then wins again).
set -euo pipefail
test "$(id -u)" = 0 || { echo "run with sudo"; exit 1; }
ssid=""
for i in $(seq 10); do
    nmcli dev wifi rescan ifname wlan0 2>/dev/null || true
    sleep 6
    ssid=$(nmcli -g SSID dev wifi list ifname wlan0 | grep -i 'sarthak' | head -1 || true)
    [[ -n $ssid ]] && break
    echo "hotspot not visible yet ($i/10)"
done
[[ -n $ssid ]] || { nmcli -f SSID,SIGNAL,CHAN dev wifi list; echo "HOTSPOT NOT FOUND"; exit 1; }
echo "Joining: $ssid"
nmcli --ask dev wifi connect "$ssid" ifname wlan0
nmcli con modify "$ssid" ipv4.route-metric 50 ipv6.route-metric 50 connection.autoconnect-priority 10
nmcli con up "$ssid"
ip route | grep default
for host in deb.debian.org github.com; do getent hosts "$host" >/dev/null && echo "DNS ok: $host"; done
ping -c2 -W3 8.8.8.8 | tail -1
echo "HOTSPOT JOINED"
