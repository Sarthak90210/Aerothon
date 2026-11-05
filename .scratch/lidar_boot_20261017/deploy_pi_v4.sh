#!/usr/bin/env bash
set -euo pipefail
workspace=/home/pi5/aerothon_ws
task=/home/pi5/.local/state/aerothon/lidar_boot_20261017
python3 "$workspace/scripts/pi_runtime/stop_runtime.py"
systemctl stop aerothon-gcs.service
tar -czf "$task/before_stream_v4.tar.gz" -C "$workspace" \
  src scripts/pi_runtime scripts/mav_router.py scripts/check_pi_runtime.sh \
  gcs AGENTS.md MASTER_DOCUMENTATION.md runtime_manifest.json
sha256sum "$task/before_stream_v4.tar.gz" > "$task/before_stream_v4.sha256"
python3 - <<'PY'
import hashlib,json,os,zipfile
from pathlib import Path
root=Path('/home/pi5/aerothon_ws')
archive=Path('/home/pi5/.local/state/aerothon/lidar_boot_20261017/runtime-v4.zip')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='d92cee475b946e6dbe0661df3f812fffa33cc67f3fd37b78b1377e2b2c87a74e'
changed=[]
with zipfile.ZipFile(archive) as z:
    manifest=json.loads(z.read('runtime_manifest.json'))
    for name,digest in manifest['files'].items():
        target=(root/name).resolve();assert target.is_relative_to(root)
        data=z.read(name);assert hashlib.sha256(data).hexdigest()==digest
        if not target.exists() or target.read_bytes()!=data:
            target.parent.mkdir(parents=True,exist_ok=True)
            temp=target.with_name(target.name+'.lidar-update')
            temp.write_bytes(data);temp.chmod(0o755 if name.endswith('.sh') else 0o644)
            os.chown(temp,1000,1000);temp.replace(target);changed.append(name)
    (root/'runtime_manifest.json').write_text(json.dumps(manifest,indent=2))
    for name,digest in manifest['files'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
print('SOURCE VERIFIED',len(manifest['files']),'files; changed',changed)
PY
docker run --rm --user 1000:1000 --workdir /workspace \
  --mount "type=bind,src=$workspace,dst=/workspace" aerothon-runtime:20261014 /bin/bash -c '
    source /opt/ros/jazzy/setup.bash
    source install/setup.bash
    colcon build --base-paths src/aerothon_runtime src/aerothon_gcs/gcs_aggregator \
      --packages-select aerothon_runtime gcs_aggregator --executor sequential --symlink-install
    bash scripts/check_pi_runtime.sh
  '
systemctl start aerothon-gcs.service
date -Is
printf 'STREAM V4 UPDATE COMPLETE\n'
