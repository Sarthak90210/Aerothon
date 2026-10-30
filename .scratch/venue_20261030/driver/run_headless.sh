#!/bin/bash
# Headless case grid (navigation-only object fixture: real search, corridors
# and landing; the delivery leaf is not exercised). Each world's dimensions
# reach the aircraft through the GCS as an operator preset made from its
# .dims.json. PAR at a time (default 1), staggered, each run in its own ROS
# domain block, at RTF x real time (default 1.0). Batch b (3 at a time, RTF 2)
# starved the corridor controller: velocity setpoints at ~2 Hz of sim time.
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"
source /opt/ros/jazzy/setup.bash
source install/setup.bash
OUT="${1:-logs/venue_20261030/headless}"
shift || true
WORLDS=("$@")
[ ${#WORLDS[@]} -gt 0 ] || WORLDS=(logs/venue_20261030/worlds/venue_c*.json)
if pgrep -af '(^|/)(arducopter|gz sim)' >/dev/null; then echo "refusing: a simulator is running"; exit 2; fi
mkdir -p "$OUT"
i=0
for w in "${WORLDS[@]}"; do
  case "$w" in *.dims.json) continue;; esac
  name=$(basename "$w" .json)
  dom=$((100 + 10 * i))
  python3 sim/fly_headless.py "$w" --conditions calm --seeds 1 --navigation-only \
    --gcs-preset "Venue headless: $name" --gcs-create-from-file "${w%.json}.dims.json" \
    --rtf "${RTF:-1.0}" --out "$OUT" --domain-base $dom > "$OUT/$name.fly.log" 2>&1 &
  i=$((i + 1))
  if (( i % ${PAR:-1} == 0 )); then wait; else sleep 20; fi
done
wait
grep -h -A3 "summary\|PASS\|FAIL" "$OUT"/*.fly.log | tail -60
