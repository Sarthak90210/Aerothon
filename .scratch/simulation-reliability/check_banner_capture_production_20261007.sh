#!/usr/bin/env bash
set -eo pipefail
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=225 ROS_LOCALHOST_ONLY=1
exec /usr/bin/python3 -m pytest sim/test_banner_capture_contract.py sim/test_banner_identity.py sim/test_banner_sweep.py sim/test_banner_orbit.py -q
