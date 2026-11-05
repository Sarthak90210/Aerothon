set -euo pipefail
test "$(id -u)" = 0
deploy=/home/pi5/aerothon-deploy
workspace=/home/pi5/aerothon_ws
cd "$deploy"
docker image inspect aerothon-dependencies:20261014 >/dev/null
DOCKER_BUILDKIT=0 docker build --network host \
    --build-arg http_proxy=http://127.0.0.1:3128 \
    --build-arg https_proxy=http://127.0.0.1:3128 \
    --build-arg no_proxy=127.0.0.1,localhost \
    -t aerothon-runtime:20261014 .
sudo -u pi5 python3 "$deploy/extract_runtime.py"
sudo -u pi5 env HTTPS_PROXY=http://127.0.0.1:3128 \
    git clone https://github.com/ldrobotSensorTeam/ldlidar_stl_ros2.git "$workspace/src/ldlidar_stl_ros2"
sudo -u pi5 git -C "$workspace/src/ldlidar_stl_ros2" checkout --detach bf668a89baf722a787dadc442860dcbf33a82f5a
driver="$workspace/src/ldlidar_stl_ros2"
python3 - "$driver" "$deploy" <<'PY'
import hashlib, json
from pathlib import Path
import subprocess, sys
root, deploy = map(Path, sys.argv[1:])
revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
files = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in root.rglob('*') if p.is_file() and '.git' not in p.parts and p.suffix != '.md'}
(deploy/'external_driver.json').write_text(json.dumps(dict(repository='https://github.com/ldrobotSensorTeam/ldlidar_stl_ros2', revision=revision, files=files), indent=2)+'\n')
PY
# External-driver README and Git data are development material; keep its licence/source.
find "$driver" -type f -name '*.md' -delete
rm -rf -- "$driver/.git"
chown -R pi5:pi5 "$deploy"
install -d -o pi5 -g pi5 /home/pi5/.aerothon /home/pi5/.local/state/aerothon/roslogs
docker run --rm --network host --user 1000:1000 \
    --mount "type=bind,src=$workspace,dst=/workspace" \
    aerothon-runtime:20261014 /bin/bash -c \
    'set -e; source /opt/ros/jazzy/setup.bash; colcon build --symlink-install --parallel-workers 2 --cmake-args -DBUILD_TESTING=OFF; source install/setup.bash; bash scripts/check_pi_runtime.sh'
docker image inspect aerothon-runtime:20261014 --format '{{.Id}} {{.Architecture}} {{.Size}}'
