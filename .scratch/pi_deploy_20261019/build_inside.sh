#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
cd /workspace
echo 'Architecture:'
uname -m
colcon list --base-paths src
colcon --log-base log/build_20261019 build --base-paths src \
  --build-base build_20261019 --install-base install_20261019 \
  --symlink-install --parallel-workers 2 --cmake-args -DBUILD_TESTING=OFF
source install_20261019/setup.bash
for package in aerothon_runtime aerothon_slam_grid mission_bringup mission_bt uav_description avoidance winch_ctrl camera_ctrl perception_qr perception_banner perception_redzone perception_overlay gcs_aggregator sllidar_ros2 ldlidar_stl_ros2; do
  ros2 pkg prefix "$package"
done
python3 - <<'PY'
import importlib
for name in ['aerothon_runtime.web','aerothon_runtime.execution_node','gcs_aggregator.aggregator','winch_ctrl.winch_node']:
    module=importlib.import_module(name)
    print('IMPORT',name,module.__file__)
PY
