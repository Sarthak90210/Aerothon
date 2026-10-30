#!/bin/bash
# AprilTag field markers (29 Oct 2026): the four field-PDF worlds, now printed
# with AprilTag 36h11 boards (IDs 100-500, start = the target pad's ID), flown
# one after another through the world maker and the GCS, each graded by
# sim/check_track.py (regressions.sh -> field_run.sh). The first three at the
# venue file's search_speed_override_mps (5.56), as r13-r15b; the r9 world
# (red zone on the return axis) paced on the detectors, as r16b/r19/r20,
# with the venue file restored on any exit.
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"
S="$(dirname "$0")"
D=logs/aruco_markers_20261029
mkdir -p "$D"
V=src/aerothon_sim/sim_gazebo/config/world_sim_venue.yaml
cp "$V" "$D/world_sim_venue.before.yaml"
restore() { cp "$D/world_sim_venue.before.yaml" "$V"; echo "$(date -Is) venue restored: $(grep search_speed_override_mps "$V")"; }
trap restore EXIT
echo "$(date -Is) venue: $(grep search_speed_override_mps "$V")"
bash "$S/regressions.sh" \
  aerothon26_field "$D/aerothon26_field_tags" c \
  aerothon26_field_L10 "$D/aerothon26_field_L10_tags" a \
  aerothon26_field_red_by_c "$D/aerothon26_field_red_by_c_tags" c
sed -i 's/^    search_speed_override_mps: 5\.56/    search_speed_override_mps: 0.0/' "$V"   # no $ anchor: CRLF-safe
grep -q '^    search_speed_override_mps: 0.0' "$V" || { echo "$(date -Is) refusing: override not set to 0.0"; exit 2; }
echo "$(date -Is) paced venue: $(grep search_speed_override_mps "$V")"
bash "$S/regressions.sh" aerothon26_field_red_near_c "$D/aerothon26_field_red_near_c_tags_paced" c
curl -s -m 90 -X POST http://127.0.0.1:8777/api/sim/stop; echo
echo "$(date -Is) run_all done"
