#!/bin/bash
# Rerun of r19 (the last pass: aerothon26_field_red_near_c, 26 Oct, source ac75470, 14/14) on the
# current source: same world, same paced search (search_speed_override_mps 0 for this run,
# restored on any exit), same driver (regressions.sh -> field_run.sh -> sim/check_track.py).
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"; mkdir -p logs/sim_rerun_20261029
S="$(dirname "$0")"
D=logs/sim_rerun_20261029
V=src/aerothon_sim/sim_gazebo/config/world_sim_venue.yaml
cp "$V" "$D/world_sim_venue.before_r20.yaml"
restore() { cp "$D/world_sim_venue.before_r20.yaml" "$V"; echo "$(date -Is) venue restored: $(grep search_speed_override_mps "$V")"; }
trap restore EXIT
sed -i 's/^    search_speed_override_mps: 5\.56/    search_speed_override_mps: 0.0/' "$V"   # no $ anchor: the file may have CRLF line ends
grep -q '^    search_speed_override_mps: 0.0' "$V" || { echo "$(date -Is) refusing: override not set to 0.0"; exit 2; }
echo "$(date -Is) r20 venue: $(grep search_speed_override_mps "$V")"
bash "$S/regressions.sh" aerothon26_field_red_near_c $D/aerothon26_field_red_near_c_r20_current c
