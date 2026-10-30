#!/bin/bash
# Graded laptop-simulation run of a field-PDF WORLD (default aerothon26_field) at the venue's
# search_speed_override_mps (5.56 m/s, 20 km/h): OUT_DIR.
# Launch via the world maker; watch Gazebo and resume it if it is paused (logged);
# Connect only once the gateway has the FCU heartbeat (refuse otherwise); enter
# organiser inputs through the GCS; record (graded track + runtime/sim bags +
# chase camera); Start; wait for the result; encode the chase video.
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"
S="$(dirname "$0")"
OUT="$1"
export WORLD="${WORLD:-aerothon26_field}"
[ -e "$OUT" ] && { echo "refusing: $OUT exists"; exit 2; }
if pgrep -af '(^|/)(arducopter|gz sim)' >/dev/null; then echo "refusing: a simulator is running"; exit 2; fi
mkdir -p "$OUT"
echo "$(date -Is) start $WORLD"
curl -s -m 120 -X POST "http://127.0.0.1:8777/api/sim/start/$WORLD"; echo
export GZ_PARTITION=aerothon_m2 GZ_IP=127.0.0.1
for i in $(seq 60); do timeout 5 gz service -l 2>/dev/null | grep -q '^/world/mission2/control$' && break; sleep 2; done
/usr/bin/python3 "$S/gz_pause_watch.py" "$OUT" "$OUT/watch_stop" > "$OUT/gz_pause_watch.log" 2>&1 &
WATCH=$!
for i in $(seq 120); do curl -s -m 5 http://127.0.0.1:8899/api/check >/dev/null 2>&1 && break; sleep 5; done
# Connect only once the gateway has the FCU's heartbeat: a manifest read
# before it has no system id, and the runtime latches an identity mismatch.
HB=no
for i in $(seq 120); do curl -s -m 5 http://127.0.0.1:8090/manifest | grep -q '"system_id": 1' && { HB=yes; break; }; sleep 5; done
echo "$(date -Is) FCU heartbeat at gateway: $HB"
if [ "$HB" != yes ]; then
    echo "NOT FLOWN: no FCU heartbeat at the gateway within 600 s" > "$OUT/RESULT.txt"
    touch "$OUT/watch_stop"; wait $WATCH; cat "$OUT/gz_pause.log"; exit 3
fi
sleep 10
curl -s -m 120 -X POST -H 'Content-Type: application/json' -d '{"profile_id":"world_sim"}' http://127.0.0.1:8899/api/connect | head -c 300; echo
python3 "$S/apply_field_inputs.py" "$WORLD" | tee "$OUT/inputs.log"
cp /tmp/aerothon_arena_layout.json "$OUT/layout.json"
cp "sim/worlds/$WORLD.json" "$OUT/world.json"
git rev-parse HEAD > "$OUT/git_head.txt"
git status --short > "$OUT/git_status.txt"
sha256sum src/aerothon_payload/winch_ctrl/winch_ctrl/winch_node.py src/aerothon_runtime/aerothon_runtime/gateway.py \
  src/aerothon_sim/sim_gazebo/config/remote_devices.parm scripts/launch_level6_sim.sh \
  src/aerothon_perception/camera_ctrl/camera_ctrl/camera_ctrl_node.py \
  src/aerothon_perception/perception_qr/perception_qr/qr_node.py \
  src/aerothon_perception/perception_qr/perception_qr/tag_decode.py \
  src/aerothon_perception/perception_qr/perception_qr/qr_match.py \
  scripts/materialize_world.py scripts/world_spec.py \
  src/aerothon_sim/sim_gazebo/materials/tag36h11_matrices.json \
  src/aerothon_perception/perception_redzone/perception_redzone/redzone_node.py \
  src/aerothon_mission/mission_bt/mission_bt/mission_tree.py src/aerothon_mission/mission_bt/mission_bt/mav_commander.py \
  src/aerothon_mission/mission_bt/mission_bt/detector_timing.py src/aerothon_mission/mission_bt/mission_bt/scan_geometry.py \
  src/aerothon_mission/mission_bt/mission_bt/search_braking.py src/aerothon_mission/mission_bt/mission_bt/decode_hover.py \
  src/aerothon_avoidance/avoidance/avoidance/local_planner.py src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py \
  src/aerothon_mission/mission_bringup/launch/mission2.launch.py src/aerothon_sim/sim_gazebo/config/world_sim_venue.yaml \
  "$HOME/.local/state/aerothon-world-sim/profiles.json" > "$OUT/source_sha256.txt"
git diff HEAD > "$OUT/worktree.diff"
bash "$S/param_probe.sh" > "$OUT/fc_winch_params.txt" 2>&1
set +u; source /opt/ros/jazzy/setup.bash; source install/setup.bash; set -u
export ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
/usr/bin/python3 "$S/record_world_sim.py" "$OUT" 5400 > "$OUT/recorder.log" 2>&1 &
bash "$S/bag_run.sh" "$OUT" > "$OUT/bag_run.log" 2>&1 &
BAG=$!
# Evaluation only: camera frames at the gates (banner detector checks).
ROS_DOMAIN_ID=42 /usr/bin/python3 "$S/banner_frames.py" "$OUT" > "$OUT/banner_frames.log" 2>&1 &
FRAMES=$!
# Evaluation-only chase camera (Gazebo native, no ROS output).
/usr/bin/python3 sim/record_chase.py --out "$OUT" --stop-file "$OUT/chase_stop" > "$OUT/chase.log" 2>&1 &
CHASE=$!
for i in $(seq 60); do [ -f "$OUT/chase/ready.json" ] && break; sleep 2; done
sleep 15
STARTED=no
for i in 1 2 3 4 5; do python3 "$S/start_mission.py" | tee -a "$OUT/start.log" | tail -1 | grep -q '"Running"' && { STARTED=yes; break; }; sleep 3; done
if [ "$STARTED" = yes ]; then
    echo "$(date -Is) started; waiting for the result"
else
    # Not two hours of waiting on a mission that never began (29 Oct, red_by_c).
    echo "NOT FLOWN: Start was never accepted (start.log)" > "$OUT/RESULT.txt"
    echo "$(date -Is) NOT FLOWN: Start was never accepted"
    touch "$OUT/not_flown"
fi
wait $BAG
cat "$OUT/bag_run.log"
touch "$OUT/chase_stop" "$OUT/watch_stop" "$OUT/frames_stop"; wait $CHASE; wait $WATCH; wait $FRAMES
echo "== gz pause log"; cat "$OUT/gz_pause.log"
/usr/bin/python3 sim/encode_chase.py "$OUT" --speed 2 --from-state ARMING > "$OUT/chase_encode.log" 2>&1
cat "$OUT/chase_encode.log"
echo "$(date -Is) done"
