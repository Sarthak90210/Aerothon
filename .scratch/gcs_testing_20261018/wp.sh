#!/usr/bin/env bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
PYTHONPATH=src/aerothon_mission/mission_bt /usr/bin/python3 - <<'PY'
from mission_bt.geofence import local_to_global
home=(-35.3632439, 149.1652163)
for x,y in ((14,2),(20,0)):
    lat,lon=local_to_global(x,y,*home); print(f"{x},{y}: {lat:.7f}, {lon:.7f}")
PY
