#!/usr/bin/env bash
set -euo pipefail
workspace=/home/pi5/aerothon_ws
task=/home/pi5/.local/state/aerothon/lidar_boot_20261017
tar -czf "$task/before_router_v3.tar.gz" -C "$workspace" scripts/mav_router.py MASTER_DOCUMENTATION.md runtime_manifest.json
systemctl stop aerothon-router.service
trap 'systemctl start aerothon-router.service' EXIT
python3 - <<'PY'
import hashlib,json,os,zipfile
from pathlib import Path
root=Path('/home/pi5/aerothon_ws')
archive=Path('/home/pi5/.local/state/aerothon/lidar_boot_20261017/runtime-v3.zip')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='c0c1da206e5973b6aa0f664938695fa8d2c03b84e71c6fd605b85681f56d3b64'
changed=[]
with zipfile.ZipFile(archive) as z:
    manifest=json.loads(z.read('runtime_manifest.json'))
    for name,digest in manifest['files'].items():
        target=(root/name).resolve();assert target.is_relative_to(root)
        data=z.read(name);assert hashlib.sha256(data).hexdigest()==digest
        if target.read_bytes()!=data:
            temporary=target.with_name(target.name+'.lidar-update')
            temporary.write_bytes(data);temporary.chmod(0o755 if name.endswith('.sh') else 0o644)
            os.chown(temporary,1000,1000);temporary.replace(target);changed.append(name)
    (root/'runtime_manifest.json').write_text(json.dumps(manifest,indent=2))
    for name,digest in manifest['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
print('SOURCE VERIFIED',len(manifest['files']),'files; changed',changed)
PY
systemctl start aerothon-router.service
trap - EXIT
date -Is
printf 'ROUTER UPDATE COMPLETE\n'
