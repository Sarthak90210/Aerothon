#!/usr/bin/env bash
# Local GCS test stack: fake vehicle + real aggregator + real web host.
set -u
repo='/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
here="$repo/.scratch/gcs_testing_20261018"
state="$here/state"; mkdir -p "$state"
set +u; source /opt/ros/jazzy/setup.bash; set -u
export FASTDDS_BUILTIN_TRANSPORTS=SHM
unset ROS_LOCALHOST_ONLY
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-77}
export PYTHONPATH="$repo/src/aerothon_gcs/gcs_aggregator:$repo/src/aerothon_mission/mission_bt:$repo/src/aerothon_perception/perception_banner:$repo/src/aerothon_runtime:$PYTHONPATH"
export AEROTHON_MAP_ONLINE=0
[ -e "$state/map-tiles" ] || ln -s ../../india_map_20261018/tiles "$state/map-tiles"
pids=()
trap 'kill ${pids[@]} 2>/dev/null; wait' EXIT INT TERM
/usr/bin/python3 "$here/fake_vehicle.py" > "$here/fake_vehicle.log" 2>&1 & pids+=($!)
/usr/bin/python3 -m gcs_aggregator.aggregator --ros-args -p managed:=true \
  -p dimension_presets_file:="$state/presets.json" > "$here/aggregator.log" 2>&1 & pids+=($!)
/usr/bin/python3 "$here/run_web.py" "$repo/src/aerothon_gcs/tauri_app/dist" "$state" ${PORT:-8897} > "$here/web.log" 2>&1 & pids+=($!)
/opt/ros/jazzy/lib/web_video_server/web_video_server --ros-args -p port:=8080 > "$here/video.log" 2>&1 & pids+=($!)
if [ "${REAL_SLAM:-0}" = 1 ]; then
  sleep 3
  ros2 run slam_toolbox async_slam_toolbox_node --ros-args --params-file "$here/slam_params.yaml" > "$here/slam.log" 2>&1 & pids+=($!)
  ros2 run nav2_lifecycle_manager lifecycle_manager --ros-args -r __node:=lifecycle_manager_slam --params-file "$here/slam_params.yaml" > "$here/lifecycle.log" 2>&1 & pids+=($!)
fi
wait
