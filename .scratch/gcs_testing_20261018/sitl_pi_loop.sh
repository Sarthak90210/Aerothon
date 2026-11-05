#!/usr/bin/env bash
# The Pi container's pattern: restart the web host in a loop, keep this shell
# (and so the runtime it launches) alive across web-host restarts.
while true; do
  bash "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/gcs_testing_20261018/sitl_pi.sh"
  echo "web host exited $?; restarting" >&2
  sleep 2
done
