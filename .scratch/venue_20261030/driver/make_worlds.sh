#!/bin/bash
# The venue worlds (scripts/venue_world.py): three rendered acceptance worlds
# in sim/worlds, and the headless case grid in logs/venue_20261030/worlds,
# each with its arena dimensions as a GCS preset file beside it.
set -e
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"
source /opt/ros/jazzy/setup.bash
V="python3 scripts/venue_world.py"
$V --out sim/worlds/aerothon26_venue.json
$V --reach-m 1.5 --first-side right --gap-m 1.5 --pads far --red before-exit --target b \
   --out sim/worlds/aerothon26_venue_far.json
$V --reach-m 1.0 --first-side left --pads spread --red mid-right --target d \
   --out sim/worlds/aerothon26_venue_r10.json
W=logs/venue_20261030/worlds; mkdir -p $W
n=0
for case in "1.0 2.0 left spread centre e" "1.0 2.0 right far mid-left a" \
            "1.25 2.0 left far mid-right c" "1.25 2.0 right spread before-exit b" \
            "1.5 2.0 left spread mid-left c" "1.5 2.0 right far centre d" \
            "1.5 1.5 left far before-exit e" "1.5 1.5 right spread mid-right a" \
            "1.0 1.5 left spread before-exit d" "1.25 1.5 right far mid-left b"; do
  set -- $case
  n=$((n+1)); name=$(printf "venue_c%02d_r%s_g%s_%s" $n ${1/./} ${2/./} $3)
  $V --reach-m $1 --gap-m $2 --first-side $3 --pads $4 --red $5 --target $6 --out $W/$name.json | grep -v "^warning"
done
$V --marker-ahead-m 1.0 --out $W/venue_c11_marker100.json | grep -v "^warning"
python3 - <<'PY'
import json, glob
for f in glob.glob("logs/venue_20261030/worlds/*.json"):
    if f.endswith(".dims.json"):
        continue
    s = json.load(open(f))
    json.dump(s["dimensions"], open(f[:-5] + ".dims.json", "w"), indent=1)
PY
ls $W | wc -l
