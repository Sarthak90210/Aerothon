"""Restore only after matching the exact pre-edit source hash."""
import hashlib
import json
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2]
source='sim/test_scan_geometry.py'
manifest=json.loads((root/'logs/reliability_render_my_world_s20261003_retry2_20261005/source_manifest.json').read_text())
original=subprocess.check_output(['git','show','HEAD:'+source],cwd=root)
assert hashlib.sha256(original).hexdigest()==manifest[source], 'HEAD differs from preserved pre-edit source; do not overwrite'
path=root/source
new=root/'sim/test_lidar_registration.py'
assert not new.exists()
new.write_bytes(path.read_bytes())
path.write_bytes(original)
print('Original geometry tests restored byte-for-byte; new tests preserved separately')
