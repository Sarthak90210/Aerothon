#!/usr/bin/env bash
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
export PATH="/home/sarthak/.nvm/versions/node/v24.18.0/bin:/usr/bin:/bin:$PATH"
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=221
out="${1:-logs/reliability_full_20261006.log}"
[[ ! -e "$out" ]] || { echo 'Output exists'; exit 2; }
bash scripts/run_tests.sh > "$out" 2>&1
