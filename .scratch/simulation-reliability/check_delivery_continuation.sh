#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=219
python3 -m pytest -q sim/test_delivery_observer.py sim/test_fail_closed_stages.py sim/test_navigation_fixture.py sim/test_delivery_retry_observation_windows.py sim/test_delivery_provisional_release_probe.py sim/test_delivery_candidate_recovery.py
python3 -m py_compile sim/run_navigation_campaign.py sim/evaluate_recorded_mission.py
