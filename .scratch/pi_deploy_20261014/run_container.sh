#!/usr/bin/env bash
set -euo pipefail
deploy=/home/pi5/aerothon-deploy
workspace=/home/pi5/aerothon_ws
source "$deploy/runtime.env"
mode=${1:?console, mission or check required}
args=(run --rm --init --network host --user 1000:1000 --cap-drop ALL
      --security-opt no-new-privileges --group-add 20 --group-add 44
      --env ROS_LOCALHOST_ONLY=1 --env ROS_DOMAIN_ID=42
      --env ROS_LOG_DIR=/home/aerothon/state/roslogs
      --mount "type=bind,src=$workspace,dst=/workspace"
      --mount "type=bind,src=$deploy,dst=/deployment,readonly"
      --mount "type=bind,src=/home/pi5/.aerothon,dst=/home/aerothon/.aerothon"
      --mount "type=bind,src=/home/pi5/.local/state/aerothon,dst=/home/aerothon/state")
for device in "$AEROTHON_CAMERA_DEVICE" "$AEROTHON_LIDAR_DEVICE"; do
    [[ ! -c $device ]] || args+=(--device "$device")
done
if [[ -n ${AEROTHON_DELIVERY_CALIBRATION:-} ]]; then
    [[ $AEROTHON_DELIVERY_CALIBRATION = /home/pi5/.aerothon/* ]] || {
        echo 'Put the measured load profile under /home/pi5/.aerothon.' >&2; exit 1;
    }
    args+=(--env "AEROTHON_DELIVERY_CALIBRATION=/home/aerothon/.aerothon/${AEROTHON_DELIVERY_CALIBRATION##*/}")
fi
case $mode in
    console) args+=(--name aerothon-console --stop-signal SIGINT --stop-timeout 30)
        command='source /opt/ros/jazzy/setup.bash; source /workspace/install/setup.bash; exec ros2 launch /deployment/console.launch.py' ;;
    mission) args+=(--name aerothon-mission --stop-signal SIGINT --stop-timeout 30)
        command="source /opt/ros/jazzy/setup.bash; source /workspace/install/setup.bash; exec ros2 launch mission_bringup mission2.launch.py use_sim:=false rviz:=false slam:=false airframe:=cad fcu_url:=udp://127.0.0.1:14555@127.0.0.1:14556 camera_device:=$AEROTHON_CAMERA_DEVICE lidar_port:=$AEROTHON_LIDAR_DEVICE lidar_yaw_deg:=$AEROTHON_LIDAR_YAW_DEG lidar_mirrored:=$AEROTHON_LIDAR_MIRRORED camera_hfov:=$AEROTHON_CAMERA_HFOV camera_exposure:=$AEROTHON_CAMERA_EXPOSURE" ;;
    check) command='bash /workspace/scripts/check_pi_runtime.sh' ;;
    *) echo 'Unknown mode' >&2; exit 2 ;;
esac
exec /usr/bin/docker "${args[@]}" "$AEROTHON_IMAGE" /bin/bash -c "$command"
