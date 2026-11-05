#!/usr/bin/env bash
# Bench drive of the payload winch through the running GCS runtime (props off,
# disarmed):  ~/winch.sh lower | stow | stop | status
# lower runs until the timed estimate reaches max_payout_m; send stop sooner.
set -euo pipefail
cmd=${1:-}
case $cmd in
    lower|stow|stop) ros="ros2 topic pub --once /winch/cmd std_msgs/msg/String '{data: $cmd}'" ;;
    status) ros="timeout 15 ros2 topic echo --once --full-length /winch/status std_msgs/msg/String" ;;
    *) echo "usage: winch.sh lower|stow|stop|status"; exit 2 ;;
esac
docker exec aerothon-runtime bash -c "source /opt/ros/jazzy/setup.bash && source /workspace/install/setup.bash && $ros"
