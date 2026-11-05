#!/usr/bin/env bash
# Non-root build on the reinstalled Pi (master guide section 5), as pi5:
#   nohup bash ~/build_pi.sh > ~/.local/state/aerothon/deploy_20261025/build.log 2>&1 &
# C1 lidar driver at its pinned revision, the two pinned images, then colcon
# inside the runtime image as the runtime's own user. Arms nothing.
set -euo pipefail
# 25 Oct: the first attempt reset the Pi (undervoltage) under full load;
# builds are capped at two cores until the supply is replaced.
ws=/home/pi5/aerothon_ws
echo "$(date -Is) start"
if [[ ! -d $ws/src/sllidar_ros2 ]]; then
    git clone -q https://github.com/Slamtec/sllidar_ros2.git "$ws/src/sllidar_ros2"
fi
git -C "$ws/src/sllidar_ros2" checkout -q 34300099fadfc772965962dec837bf436706188f
git -C "$ws/src/sllidar_ros2" log -1 --format='sllidar_ros2 %H'
cd "$ws/scripts/pi_runtime"
echo "$(date -Is) building aerothon-dependencies:20261014"
DOCKER_BUILDKIT=0 docker build --cpuset-cpus 0,1 -t aerothon-dependencies:20261014 -f Dockerfile.dependencies .
echo "$(date -Is) building aerothon-runtime:20261014"
DOCKER_BUILDKIT=0 docker build --cpuset-cpus 0,1 -t aerothon-runtime:20261014 -f Dockerfile .
docker image ls --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}' | grep aerothon
echo "$(date -Is) colcon build"
docker run --rm --cpus 1 --user 1000:1000 --network none \
    --mount "type=bind,src=$ws,dst=/workspace" aerothon-runtime:20261014 /bin/bash -c \
    'source /opt/ros/jazzy/setup.bash && cd /workspace && colcon build --symlink-install --parallel-workers 1'
echo "$(date -Is) BUILD COMPLETE"
