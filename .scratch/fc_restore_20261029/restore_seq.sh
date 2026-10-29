#!/bin/bash
# On the Pi: finish the FC restore through the router. Runtime off (load), confirm
# pass, FC reboot (refused if armed), second pass for parameters that exist only
# after the reboot, read back the key values, runtime back on.
set -u
cd /home/pi5/.local/state/aerothon/fc_reset_20261029
export MAVLINK20=1 MAVLINK_DIALECT=ardupilotmega PYTHONPATH=/home/pi5/.local/state/aerothon/deploy_20261027b/pylib
api=http://127.0.0.1:8899
echo "$(date -Is) start; $(uptime)"
curl -s -m 40 -X POST -H 'Content-Type: application/json' -d '{}' $api/api/disconnect >/dev/null && echo "runtime disconnected"
sleep 5
echo "== pass A (confirm)"; python3 -u fc_write_params.py fc_restore_20261029.param
echo "== reboot"; python3 -u ../deploy_20261027b/fc_reboot.py || { echo "reboot refused or failed"; exit 2; }
sleep 10
echo "== pass B"; python3 -u fc_write_params.py fc_restore_20261029.param
echo "== key values"
python3 -u fc_read_some.py udpout:127.0.0.1:14550 SERVO5_FUNCTION MNT1_TYPE SERIAL1_PROTOCOL SERIAL1_BAUD \
  SERIAL2_PROTOCOL SERIAL2_BAUD SERIAL5_PROTOCOL SERIAL5_BAUD SERIAL5_OPTIONS MAV2_OPTIONS OSD_TYPE OSD1_ENABLE \
  RSSI_TYPE FLTMODE_CH FS_THR_ENABLE FRAME_CLASS GPS1_TYPE
curl -s -m 60 -X POST -H 'Content-Type: application/json' -d '{"profile_id": "vehicle"}' $api/api/connect \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("runtime", d.get("runtime"), d.get("connection_error") or "")'
echo "$(date -Is) DONE"
