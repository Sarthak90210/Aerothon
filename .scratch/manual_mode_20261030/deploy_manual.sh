#!/usr/bin/env bash
# Destination update 20261030-manual, run as pi5 on the Pi. Adds the GCS
# "Manual flight" profile mode (launch manual:=true: MAVROS, stream rates,
# rc_in_bridge, camera_ctrl, winch_ctrl, the aggregator and the raw webcam
# feed: usb_cam, camera_exposure, web_video_server). Installs
# exactly four sources (HEAD 82ab2b8 + manual mode) and the GCS built from
# the same; nothing else in the workspace changes. --symlink-install: no
# rebuild. The runtime is stopped first; only the web host is restarted.
#
#   bash deploy_manual.sh --dry-run    verify and print what would change
#   bash deploy_manual.sh              disconnect, back up, install, restart web host
set -euo pipefail
ws=/home/pi5/aerothon_ws
task=/home/pi5/.local/state/aerothon/deploy_20261030_manual_b
api=http://127.0.0.1:8899
FILES="src/aerothon_mission/mission_bringup/launch/mission2.launch.py
src/aerothon_runtime/aerothon_runtime/web.py
src/aerothon_runtime/aerothon_runtime/contracts.py
src/aerothon_gcs/gcs_aggregator/gcs_aggregator/aggregator.py"

state() { curl -s -m 10 "$api/api/state"; }
state | python3 -c '
import json, sys
s = json.load(sys.stdin)
e = s.get("execution") or {}
active = bool(e) and e.get("state") not in {"Completed", "Failed", "Outcome unknown"}
print("runtime", s["runtime"], "| profile", s["profile_id"], "| fresh", s["fresh"], "| can_disconnect", s["can_disconnect"], "| execution", e.get("state"))
assert not active, "a task is running: finish it first"
assert s["runtime"] == "Stopped" or s["can_disconnect"], "runtime up without a confirmed disarm"'

for f in $FILES; do python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$task/$f"; done
for f in $FILES; do cmp -s "$task/$f" "$ws/$f" && echo "  same   $f" || echo "  change $f"; done
echo "  gcs: $(find "$task/gcs" -type f | wc -l) new files replace $(find "$ws/gcs" -type f | wc -l)"
[[ ${1:-} == --dry-run ]] && exit 0

# 0. Runtime off.
if [[ $(state | python3 -c 'import json,sys; print(json.load(sys.stdin)["runtime"])') != Stopped ]]; then
    curl -s -m 40 -X POST -H 'Content-Type: application/json' -d '{}' "$api/api/disconnect" | python3 -c \
        'import json,sys; d=json.load(sys.stdin); assert d.get("runtime")=="Stopped", d; print("runtime", d["runtime"])'
fi

# 1. Back up what is replaced.
stamp=$(date +%Y%m%dT%H%M%S)
tar -czf "$task/before_$stamp.tar.gz" -C "$ws" $FILES gcs runtime_manifest.json
sha256sum "$task/before_$stamp.tar.gz" | tee "$task/backups_$stamp.sha256"

# 2. Install sources and GCS, then the manifest.
for f in $FILES; do cp "$task/$f" "$ws/$f.deploy-manual"; chmod 644 "$ws/$f.deploy-manual"; mv "$ws/$f.deploy-manual" "$ws/$f"; done
rm -rf "$ws/gcs.deploy-manual"; cp -r "$task/gcs" "$ws/gcs.deploy-manual"
rm -rf "$ws/gcs.before-manual"; mv "$ws/gcs" "$ws/gcs.before-manual"; mv "$ws/gcs.deploy-manual" "$ws/gcs"; rm -rf "$ws/gcs.before-manual"
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
m['files'] = {k: v for k, v in m['files'].items() if not k.startswith('gcs/')}
for p in sorted((root / 'gcs').rglob('*')):
    if p.is_file():
        m['files'][p.relative_to(root).as_posix()] = digest(p)
m['deploy_20261030_manual'] = 'HEAD 82ab2b8 + GCS manual-flight mode (four sources, GCS)'
tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(m, indent=2)); tmp.replace(path)
bad = [k for k, v in m['files'].items() if not (root / k).is_file() or digest(root / k) != v]
print('MANIFEST', len(m['files']), 'files;', 'all verified' if not bad else f'{len(bad)} MISMATCH: {bad[:5]}')
PY

# 3. The installed links reach the changed sources. They chain through
# container paths (/workspace/...), so resolve them inside the container.
docker exec aerothon-runtime bash -c 'set -e
f=$(readlink -f /workspace/install/mission_bringup/share/mission_bringup/launch/mission2.launch.py)
[[ $f == /workspace/src/* ]] && grep -q "manual:=true" "$f"
grep -q "manual" "$(readlink -f /workspace/build/aerothon_runtime/aerothon_runtime)/web.py"
grep -q "runtime_mode" "$(readlink -f /workspace/build/gcs_aggregator/gcs_aggregator)/aggregator.py"
echo "installed links reach src/"'

# 4. Restart the web host only (its container loop relaunches it in 2 s).
docker exec aerothon-runtime pkill -f 'aerothon_runtime/web_host' || true
docker exec aerothon-runtime pkill -f 'ros2 run aerothon_runtime web_host' || true
for i in $(seq 1 30); do sleep 1; state >/dev/null 2>&1 && break; done
state | python3 -c 'import json,sys; s=json.load(sys.stdin); print("web host back: runtime", s["runtime"], "| mode field", "mode" in s)'
curl -s -m 10 "$api/" | grep -o 'assets/index-[A-Za-z0-9_-]*\.js'
echo "$(date -Is) DEPLOY 20261030-manual INSTALLED"
