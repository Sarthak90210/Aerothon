#!/usr/bin/env bash
set -euo pipefail
stage=/home/pi5/aerothon-stage/20261019-slam-ui
workspace=/home/pi5/aerothon_ws
test "$(cat "$stage/build_exit_code")" = 0
test -f "$workspace/install_20261019/setup.bash"
test ! -e "$workspace/install_before_20261019"
mv "$workspace/install" "$workspace/install_before_20261019"
ln -s install_20261019 "$workspace/install"
/bin/bash /home/pi5/aerothon-deploy/run_container.sh check > "$stage/software_check.log" 2>&1
bash "$workspace/scripts/pi_runtime/install_services.sh" > "$stage/install_services.log" 2>&1
systemctl is-active aerothon-gcs aerothon-router
readlink "$workspace/install"
vcgencmd get_throttled
vcgencmd pmic_read_adc | sed -n '/EXT5V/p'
tail -n 8 "$stage/software_check.log"
