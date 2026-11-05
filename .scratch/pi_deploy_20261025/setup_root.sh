#!/usr/bin/env bash
# Root setup for the reinstalled Pi 5 (Debian 13), run by the operator:
#   sudo bash ~/aerothon_setup_root.sh
# Installs Docker (the Jazzy runtime container route, master guide section 5),
# lets pi5 use it, and enables UART0 on GPIO14/15 (header 8/10) for the
# flight controller, as on 23 Oct 2026. Reboot afterwards for UART0 and the
# docker group to take effect. Nothing here arms, flies or changes sudo.
set -euo pipefail
test "$(id -u)" = 0 || { echo "run with sudo"; exit 1; }

apt-get update
apt-get install -y docker.io
systemctl enable docker
usermod -aG docker pi5

cfg=/boot/firmware/config.txt
[[ -f $cfg.bak-aerothon-20261025 ]] || cp -p "$cfg" "$cfg.bak-aerothon-20261025"
if ! grep -q '^dtparam=uart0=on' "$cfg"; then
    # The file ends in its [all] section.
    printf '# AeroTHON: flight controller on UART0, GPIO14 TX / GPIO15 RX (header 8/10)\ndtparam=uart0=on\n' >> "$cfg"
fi
tail -3 "$cfg"
docker --version
echo "ROOT SETUP DONE - now reboot: sudo reboot"
