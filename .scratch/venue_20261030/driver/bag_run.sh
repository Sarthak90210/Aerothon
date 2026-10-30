#!/bin/bash
# Instrumented laptop-simulation run: OUT_DIR. Runtime bag (domain 42), simulator
# truth bag (domain 43), and a wall-timestamped tail of Gazebo/SITL warnings.
# Stops when the runtime log reports a mission result or a crash, or after 2 h.
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"
set +u; source /opt/ros/jazzy/setup.bash; source install/setup.bash; set -u
OUT="$1"; mkdir -p "$OUT"
export ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ROS_DOMAIN_ID=42 ros2 bag record -o "$OUT/runtime_bag" \
  /scan /mavros/local_position/pose /mavros/local_position/velocity_local /mavros/imu/data \
  /mavros/setpoint_raw/local /mavros/setpoint_position/local /mavros/state /mission/state \
  /avoidance/detail /avoidance/status /percep/banner/detail /percep/redzone/detail /camera/pose_state /winch/status /winch/cmd \
  /percep/qr/detail /mission/target \
  > "$OUT/runtime_bag.log" 2>&1 &
B1=$!
ROS_DOMAIN_ID=43 ros2 bag record -o "$OUT/sim_bag" /odometry /clock /joint_states /winch/gz/payout > "$OUT/sim_bag.log" 2>&1 &
B2=$!
( tail -n0 -F "logs/custom/${WORLD:-shipped}_manual.log" | while IFS= read -r line; do
    case "$line" in *"has reset"*|*Crash*|*"lane switch"*|*EKF*|*Err*) echo "$(date +%s.%N) $line";; esac
  done ) > "$OUT/sim_warnings.log" 2>&1 &
T=$!
R="$HOME/.local/state/aerothon-world-sim/runtime.log"
start=$(wc -l < "$R")
for i in $(seq 1440); do
  if tail -n +"$start" "$R" | grep -aq -E "Mission result:|FCU: Crash"; then break; fi
  if grep -qE "\"state\": \"(COMPLETED|FAILED|ABORTED)\"" "$OUT/states.jsonl" 2>/dev/null; then break; fi
  [ -e "$OUT/not_flown" ] && break      # field_run.sh: Start never accepted
  sleep 5
done
sleep 30
# TERM, not INT: jobs started with & by a non-interactive bash ignore SIGINT,
# and on 29 Oct the recorders of two runs kept recording through the next
# ones until the camera fell under the readiness rate. TERM closes the bag.
kill -TERM $B1 $B2
for i in $(seq 30); do kill -0 $B1 2>/dev/null || kill -0 $B2 2>/dev/null || break; sleep 1; done
kill $T 2>/dev/null; pkill -P $T 2>/dev/null
tail -n +"$start" "$R" > "$OUT/runtime.log"
grep -a -E "Mission result:|FCU: Crash" "$OUT/runtime.log" | head -3 | cut -c1-250
