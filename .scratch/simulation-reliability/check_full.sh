#!/usr/bin/env bash
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH"
export PYTHONNOUSERSITE=1
export ROS_DOMAIN_ID=215
bash scripts/run_tests.sh --quick > logs/reliability_full_suite.log 2>&1