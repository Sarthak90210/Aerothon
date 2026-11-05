#!/usr/bin/env bash
# Local offline-map check: the production web host, online tiles disabled,
# its tile cache pointed at the downloaded tiles. No profile, so no vehicle.
set -euo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
state=.scratch/india_map_20261018/state
mkdir -p "$state"
[ -e "$state/map-tiles" ] || ln -s ../tiles "$state/map-tiles"
export PYTHONPATH="$PWD/src/aerothon_runtime"
export AEROTHON_MAP_ONLINE=0
exec /usr/bin/python3 -m aerothon_runtime.web --static src/aerothon_gcs/tauri_app/dist \
  --state-dir "$state" --bind 127.0.0.1 --port 8898
