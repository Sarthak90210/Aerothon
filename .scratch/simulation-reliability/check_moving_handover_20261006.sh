#!/usr/bin/env bash
set -euo pipefail
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
set -u
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1 ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=220
export PYTHONPATH="$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_avoidance/avoidance:$PWD/src/aerothon_payload/winch_ctrl:$PWD/src/aerothon_perception/camera_ctrl:$PWD/src/aerothon_perception/perception_qr:$PWD/src/aerothon_perception/perception_redzone:$PWD/src/aerothon_perception/perception_banner:${PYTHONPATH:-}"
python3 -m pytest sim/test_moving_return_handover.py sim/test_corridor_disarm.py sim/test_focused_return_evidence.py sim/test_qualification_evidence.py -q
python3 -m pytest sim/test_leg_routing.py sim/test_fail_closed_stages.py -q
python3 -m pytest sim/test_recording_metrics.py sim/test_navigation_campaign_gate.py -q
python3 -m py_compile sim/corridor_trial.py sim/test_moving_return_handover.py sim/qualification_evidence.py sim/record_delivery.py sim/evaluate_recorded_mission.py .scratch/simulation-reliability/grade_focused_return.py
bash -n scripts/run_recorded_acceptance.sh
printf 'Owned Python and shell syntax PASS\n'
