#!/usr/bin/env bash
set -euo pipefail
workspace=/home/pi5/aerothon_ws
task=/home/pi5/.local/state/aerothon/lidar_boot_20261017
test "$(id -u)" = 0
install -d -o pi5 -g pi5 "$task"
python3 "$workspace/scripts/pi_runtime/stop_runtime.py"
systemctl stop aerothon-gcs.service
stamp=$(date -u +%Y%m%dT%H%M%SZ)
backup="$task/before_$stamp.tar.gz"
tar -czf "$backup" -C /home/pi5 \
  aerothon_ws/src aerothon_ws/scripts aerothon_ws/gcs \
  aerothon_ws/MASTER_DOCUMENTATION.md aerothon_ws/AGENTS.md \
  aerothon-deploy .aerothon .local/state/aerothon/profiles.json \
  .local/state/aerothon/commands.sqlite
tar -tzf "$backup" >/dev/null
sha256sum "$backup" | tee "$task/backup.sha256"
python3 - <<'PY'
import hashlib,json,zipfile
from pathlib import Path
root=Path('/home/pi5/aerothon_ws')
archive=Path('/home/pi5/.local/state/aerothon/lidar_boot_20261017/runtime.zip')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='44c9deee24c871a2608399adcea195e77b2cafdd6f43bc6a81c9410340ce8525'
with zipfile.ZipFile(archive) as z:
    manifest=json.loads(z.read('runtime_manifest.json'))
    assert sorted(p for p in z.namelist() if p.endswith('.md'))==['AGENTS.md','MASTER_DOCUMENTATION.md']
    for name,digest in manifest['files'].items():
        target=(root/name).resolve()
        assert target.is_relative_to(root)
        data=z.read(name)
        assert hashlib.sha256(data).hexdigest()==digest,name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o755 if name.endswith('.sh') else 0o644)
    (root/'runtime_manifest.json').write_text(json.dumps(manifest,indent=2))
print('SOURCE VERIFIED',len(manifest['files']),'files;',len(manifest['local_ros_packages']),'local ROS packages')
PY
chown -R pi5:pi5 "$workspace/src/aerothon_slam_grid"
docker run --rm --name aerothon-build-lidar-20261017 --network host \
  --user 1000:1000 --workdir /workspace \
  --mount "type=bind,src=$workspace,dst=/workspace" \
  aerothon-runtime:20261014 /bin/bash -c '
    set -e
    source /opt/ros/jazzy/setup.bash
    source /workspace/install/setup.bash
    colcon build --base-paths src --packages-select aerothon_slam_grid mission_bringup gcs_aggregator aerothon_runtime \
      --executor sequential --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
    bash /workspace/scripts/check_pi_runtime.sh
  '
bash "$workspace/scripts/pi_runtime/install_services.sh"
systemd-analyze verify /etc/systemd/system/aerothon-router.service /etc/systemd/system/aerothon-gcs.service
systemctl restart aerothon-router.service
systemctl is-active aerothon-router.service aerothon-gcs.service
date -Is
printf 'DEPLOYMENT COMPLETE\n'
