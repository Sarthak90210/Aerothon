#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
export PYTHONPATH="$PWD/sim:$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_avoidance/avoidance:$PWD/scripts:${PYTHONPATH:-}"
python3 -m pytest sim/test_gate_braking.py sim/test_gate_motion_physics.py sim/test_gate_brake_motion_anchor.py sim/test_gate_capture_pause.py sim/test_gate_ground_displacement.py sim/test_return_camera_handoff.py sim/test_return_climb_completion.py sim/test_search_hazard_hold.py sim/test_landing_capture_gap.py sim/test_scan_motion_registration.py sim/test_altitude_hold.py sim/test_corridor_vertical_motion.py sim/test_corridor_vertical_motion_physics.py sim/test_behavior_tree.py sim/test_search_current_command.py sim/test_search_braking_20261007.py sim/test_observed_exclusion_certificate.py -q -s > logs/reliability_v38_integrated_focused_20261009.log 2>&1
