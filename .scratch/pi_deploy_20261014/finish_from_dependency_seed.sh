# Recovery path for a failed dependency download, preserving downloaded packages.
set -euo pipefail
test "$(id -u)" = 0
container=${1:?stopped dependency container required}
test "$(docker inspect "$container" --format '{{.State.Running}}')" = false
docker commit "$container" aerothon-dependency-seed:20261014
docker run --name aerothon-dependency-retry --network host \
    --entrypoint /bin/bash \
    --env http_proxy=http://127.0.0.1:3128 --env https_proxy=http://127.0.0.1:3128 \
    aerothon-dependency-seed:20261014 -c \
    'set -e; apt-get -o Acquire::Retries=3 install -y --no-install-recommends ros-jazzy-mavros ros-jazzy-mavros-extras ros-jazzy-cv-bridge ros-jazzy-web-video-server ros-jazzy-usb-cam ros-jazzy-xacro ros-jazzy-robot-state-publisher ros-jazzy-py-trees python3-opencv python3-numpy python3-scipy python3-serial python3-websockets python3-pyzbar tesseract-ocr libzbar0 geographiclib-tools; /opt/ros/jazzy/lib/mavros/install_geographiclib_datasets.sh; rm -rf /var/lib/apt/lists/*'
test "$(docker inspect aerothon-dependency-retry --format '{{.State.ExitCode}}')" = 0
docker commit aerothon-dependency-retry aerothon-dependencies:20261014
