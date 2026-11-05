#!/usr/bin/env bash
set -eo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=20
export PYTHONPATH="$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_avoidance/avoidance:$PWD/src/aerothon_perception/camera_ctrl:$PWD/src/aerothon_perception/perception_banner:$PWD/src/aerothon_perception/perception_qr:$PWD/src/aerothon_perception/perception_redzone:$PWD/sim:${PYTHONPATH:-}"
python3 -m pytest sim/test_return_capture_batching.py sim/test_banner_capture_contract.py sim/test_gate_braking.py sim/test_return_sweep_efficiency.py sim/test_return_inherited_tilt.py sim/test_return_vertical_framing.py sim/test_return_clipped_framing.py sim/test_return_fine_framing.py sim/test_return_gate_search.py sim/test_banner_sweep.py sim/test_banner_orbit.py sim/test_banner_identity.py -q 2>&1 | tee logs/reliability_v14_return_components_20261008.log
