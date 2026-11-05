#!/usr/bin/env bash
# v7: GCS offline-map regions and guide only. Static files are served per
# request, so no rebuild, service restart or root is needed. index.html last.
set -euo pipefail
workspace=/home/pi5/aerothon_ws
task=/home/pi5/.local/state/aerothon/india_map_20261018
tar -czf "$task/before_v7.tar.gz" -C "$workspace" gcs MASTER_DOCUMENTATION.md runtime_manifest.json
sha256sum "$task/before_v7.tar.gz" > "$task/before_v7.sha256"
python3 - <<'PY'
import hashlib, json, os, zipfile
from pathlib import Path
root = Path('/home/pi5/aerothon_ws')
archive = Path('/home/pi5/.local/state/aerothon/india_map_20261018/runtime-v7.zip')
assert hashlib.sha256(archive.read_bytes()).hexdigest() == '4f5e3e6079c6ecc5ad22e91ac19ed8b11f0f25222ddf075be0825eaf44862979'
changed = []
with zipfile.ZipFile(archive) as z:
    manifest = json.loads(z.read('runtime_manifest.json'))
    for name in sorted(manifest['files'], key=lambda n: n == 'gcs/index.html'):
        digest = manifest['files'][name]
        target = (root / name).resolve()
        assert target.is_relative_to(root)
        data = z.read(name)
        assert hashlib.sha256(data).hexdigest() == digest
        if not target.exists() or target.read_bytes() != data:
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_name(target.name + '.map-update')
            temp.write_bytes(data)
            temp.chmod(0o755 if name.endswith('.sh') else 0o644)
            temp.replace(target)
            changed.append(name)
    (root / 'runtime_manifest.json').write_text(json.dumps(manifest, indent=2))
    for name, digest in manifest['files'].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
print('SOURCE VERIFIED', len(manifest['files']), 'files; changed', changed)
PY
date -Is
printf 'INDIA MAP V7 UPDATE COMPLETE\n'
