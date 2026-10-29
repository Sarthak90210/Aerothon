#!/bin/bash
# Wait (up to 30 min) for COM25 to be free, then write the restore file over USB: pass 1.
cd "$(dirname "$0")"
export MAVLINK20=1 MAVLINK_DIALECT=ardupilotmega PYTHONPATH="$PWD/pylib"
for i in $(seq 900); do
  if python -c "import serial,sys; s=serial.Serial('COM25',115200,timeout=0.2); s.close()" 2>/dev/null; then
    echo "$(date -Is) COM25 free"; break
  fi
  sleep 2
done
python -c "import serial; serial.Serial('COM25',115200).close()" || { echo "COM25 still busy after 30 min"; exit 3; }
python -u fc_write_params.py fc_restore_20261029.param COM25,115200 2>&1 | tee pass1_usb.log
echo "exit ${PIPESTATUS[0]}"
