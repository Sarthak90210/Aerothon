#!/bin/bash
# Rendered venue runs with the Gazebo window open (laptop-simulation route:
# world maker, GCS web host, inputs through the GCS), one after another:
#   run_venue.sh WORLD OUT TARGET [WORLD OUT TARGET ...]
# The search is paced on the detectors as the aircraft flies it
# (search_speed_override_mps 0.0 in the simulator's venue file for the batch,
# restored on any exit). Starts the world maker if it is not already serving.
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"
S="$(dirname "$0")"
D=logs/venue_20261030
mkdir -p "$D"
V=src/aerothon_sim/sim_gazebo/config/world_sim_venue.yaml
cp "$V" "$D/world_sim_venue.before.$$.yaml"
SERVE=
restore() {
  cp "$D/world_sim_venue.before.$$.yaml" "$V"
  echo "$(date -Is) venue restored: $(grep search_speed_override_mps "$V")"
  [ -n "$SERVE" ] && kill "$SERVE" 2>/dev/null
}
trap restore EXIT
sed -i 's/^    search_speed_override_mps: 5\.56/    search_speed_override_mps: 0.0/' "$V"   # no $ anchor: CRLF-safe
grep -q '^    search_speed_override_mps: 0.0' "$V" || { echo "$(date -Is) refusing: override not set to 0.0"; exit 2; }
echo "$(date -Is) paced venue: $(grep search_speed_override_mps "$V")"
if ! curl -s -m 5 http://127.0.0.1:8777/api/sim >/dev/null; then
  /usr/bin/python3 tools/world_editor/serve.py > "$D/world_editor.$$.log" 2>&1 &
  SERVE=$!
  for i in $(seq 30); do curl -s -m 5 http://127.0.0.1:8777/api/sim >/dev/null && break; sleep 2; done
fi
echo "$(date -Is) world maker: $(curl -s -m 5 http://127.0.0.1:8777/api/sim | head -c 200)"
bash "$S/regressions.sh" "$@"
curl -s -m 90 -X POST http://127.0.0.1:8777/api/sim/stop; echo
echo "$(date -Is) run_venue done"
