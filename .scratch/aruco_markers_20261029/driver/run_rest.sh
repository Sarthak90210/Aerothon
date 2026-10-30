#!/bin/bash
# The two field worlds run_all.sh did not fly (29 Oct): red_by_c again into a
# fresh directory (its first attempt never got a Start accepted: stale
# recorders, see that run's INTERRUPTED.txt), then the r9 world paced on the
# detectors, as r16b/r19/r20, with the venue file restored on any exit.
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"
S="$(dirname "$0")"
D=logs/aruco_markers_20261029
V=src/aerothon_sim/sim_gazebo/config/world_sim_venue.yaml
cp "$V" "$D/world_sim_venue.before_rest.yaml"
restore() { cp "$D/world_sim_venue.before_rest.yaml" "$V"; echo "$(date -Is) venue restored: $(grep search_speed_override_mps "$V")"; }
trap restore EXIT
if pgrep -af "ros2 bag record|record_world_sim|record_chase" >/dev/null; then echo "$(date -Is) refusing: recorders still running"; exit 2; fi
echo "$(date -Is) venue: $(grep search_speed_override_mps "$V")"
bash "$S/regressions.sh" aerothon26_field_red_by_c "$D/aerothon26_field_red_by_c_tags_retry1" c
sed -i 's/^    search_speed_override_mps: 5\.56/    search_speed_override_mps: 0.0/' "$V"   # no $ anchor: CRLF-safe
grep -q '^    search_speed_override_mps: 0.0' "$V" || { echo "$(date -Is) refusing: override not set to 0.0"; exit 2; }
echo "$(date -Is) paced venue: $(grep search_speed_override_mps "$V")"
bash "$S/regressions.sh" aerothon26_field_red_near_c "$D/aerothon26_field_red_near_c_tags_paced" c
curl -s -m 90 -X POST http://127.0.0.1:8777/api/sim/stop; echo
pgrep -af "ros2 bag record|record_world_sim|record_chase" | cut -c1-120
echo "$(date -Is) run_rest done"
