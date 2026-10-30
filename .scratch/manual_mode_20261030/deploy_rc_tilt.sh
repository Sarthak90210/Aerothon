#!/usr/bin/env bash
# Destination update 20261030-rc-tilt, run as pi5 on the Pi. Receiver channel
# 8 becomes a tilt ANGLE through the Camera cal (low straight down, middle 45,
# high forward) instead of a raw pulse width. Installs exactly
# camera_ctrl_node.py and venue.yaml (HEAD 82ab2b8 + this change); no rebuild
# (--symlink-install). Runtime: Disconnect, install, Connect the same profile.
#
#   bash deploy_rc_tilt.sh --dry-run | bash deploy_rc_tilt.sh
set -euo pipefail
ws=/home/pi5/aerothon_ws
task=$(cd "$(dirname "$0")" && pwd)
api=http://127.0.0.1:8899
FILES="src/aerothon_perception/camera_ctrl/camera_ctrl/camera_ctrl_node.py
src/aerothon_mission/mission_bringup/config/venue.yaml"
state() { curl -s -m 10 "$api/api/state"; }
state | python3 -c '
import json, sys
s = json.load(sys.stdin)
e = s.get("execution") or {}
active = bool(e) and e.get("state") not in {"Completed", "Failed", "Outcome unknown"}
print("runtime", s["runtime"], "| profile", s["profile_id"], "| mode", s.get("mode"), "| fresh", s["fresh"], "| can_disconnect", s["can_disconnect"])
assert not active, "a task is running: finish it first"
assert s["runtime"] == "Stopped" or s["can_disconnect"], "runtime up without a confirmed disarm"'
profile=$(state | python3 -c 'import json,sys; print(json.load(sys.stdin)["profile_id"] or "")')
python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$task/src/aerothon_perception/camera_ctrl/camera_ctrl/camera_ctrl_node.py"
python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$task/src/aerothon_mission/mission_bringup/config/venue.yaml"
for f in $FILES; do cmp -s "$task/$f" "$ws/$f" && echo "  same   $f" || echo "  change $f"; done
[[ ${1:-} == --dry-run ]] && exit 0
if [[ $(state | python3 -c 'import json,sys; print(json.load(sys.stdin)["runtime"])') != Stopped ]]; then
    curl -s -m 40 -X POST -H 'Content-Type: application/json' -d '{}' "$api/api/disconnect" | python3 -c \
        'import json,sys; d=json.load(sys.stdin); assert d.get("runtime")=="Stopped", d; print("runtime", d["runtime"])'
fi
stamp=$(date +%Y%m%dT%H%M%S)
tar -czf "$task/before_$stamp.tar.gz" -C "$ws" $FILES runtime_manifest.json
sha256sum "$task/before_$stamp.tar.gz" | tee "$task/backups_$stamp.sha256"
for f in $FILES; do cp "$task/$f" "$ws/$f.deploy-rctilt"; chmod 644 "$ws/$f.deploy-rctilt"; mv "$ws/$f.deploy-rctilt" "$ws/$f"; done
python3 - "$ws" $FILES <<'PY'
import hashlib, json, sys
from pathlib import Path
root, files = Path(sys.argv[1]), sys.argv[2:]
path = root / 'runtime_manifest.json'
m = json.loads(path.read_text())
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for f in files:
    assert f in m['files'], f
    m['files'][f] = digest(root / f)
m['deploy_20261030_rc_tilt'] = 'channel 8 tilt through the Camera cal (camera_ctrl_node.py, venue.yaml)'
tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(m, indent=2)); tmp.replace(path)
bad = [k for k, v in m['files'].items() if not (root / k).is_file() or digest(root / k) != v]
print('MANIFEST', len(m['files']), 'files;', 'all verified' if not bad else f'{len(bad)} MISMATCH: {bad[:5]}')
PY
docker exec aerothon-runtime bash -c 'set -e
grep -q "_rc_angle" "$(readlink -f /workspace/build/camera_ctrl/camera_ctrl)/camera_ctrl_node.py"
grep -q "rc_tilt_low_us" "$(readlink -f /workspace/install/mission_bringup/share/mission_bringup/config/venue.yaml)"
echo "installed links reach src/"'
if [[ -n $profile ]]; then
    curl -s -m 60 -X POST -H 'Content-Type: application/json' -d "{\"profile_id\": \"$profile\"}" \
        "$api/api/connect" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("runtime", d.get("runtime"), d.get("profile_id"), d.get("mode"), d.get("connection_error") or "")'
fi
echo "$(date -Is) DEPLOY 20261030-rc-tilt INSTALLED"
