#!/usr/bin/env bash
# Destination update 20261029d, run as pi5 on the Pi: bundle
# pi-runtime-20261029d.zip (source 65fe5da). Receiver channel 8 tilts the
# camera through the Pi (camera_ctrl rc_tilt_channel 8; FC SERVO5_FUNCTION 0),
# channel 6 stays the winch's alone. Same route as deploy_pi_e.sh: existing
# files replaced, the runtime restarted, no rebuild (--symlink-install).
#
#   bash deploy_pi_g.sh --dry-run    verify and print what would change
#   bash deploy_pi_g.sh              disconnect, back up, install, reconnect
set -euo pipefail
ws=/home/pi5/aerothon_ws
task=/home/pi5/.local/state/aerothon/deploy_20261029d
archive=$task/pi-runtime-20261029d.zip
want=a3cfca5b6c0a1b62cc3c331c4914c84cde7108a6f66a1d38a2cb88d8822d1f64
api=http://127.0.0.1:8899
echo "$want  $archive" | sha256sum -c -

state() { curl -s -m 10 "$api/api/state"; }
state | python3 -c '
import json, sys
s = json.load(sys.stdin)
e = s.get("execution") or {}
active = bool(e) and e.get("state") not in {"Completed", "Failed", "Outcome unknown"}
print("runtime", s["runtime"], "| profile", s["profile_id"], "| fresh", s["fresh"], "| can_disconnect", s["can_disconnect"], "| execution", e.get("state"))
assert not active, "a task is running: finish it first"
assert s["runtime"] == "Stopped" or s["can_disconnect"], "runtime up without a confirmed disarm"'
profile=$(state | python3 -c 'import json,sys; print(json.load(sys.stdin)["profile_id"] or "")')

plan() {   # $1 = dry | apply ; prints the files to change
python3 - "$archive" "$ws" "$1" "$task" <<'PY'
import hashlib, json, sys, zipfile
from pathlib import Path
archive, root, mode, task = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
with zipfile.ZipFile(archive) as z:
    manifest = json.loads(z.read('runtime_manifest.json'))
    files = manifest['files']
    installed = json.loads((root / 'runtime_manifest.json').read_text())['files']
    added = sorted(set(files) - set(installed))
    removed = sorted(set(installed) - set(files))
    changed = sorted(n for n in files if n in installed and
                     (not (root / n).exists() or hashlib.sha256((root / n).read_bytes()).hexdigest() != files[n]))
    for name, digest in files.items():
        assert hashlib.sha256(z.read(name)).hexdigest() == digest, name
    print(len(changed), 'to change,', len(added), 'added,', len(removed), 'removed')
    for n in changed: print('  change', n)
    for n in added: print('  add', n)
    for n in removed: print('  remove', n)
    outside = [n for n in added + removed if not n.startswith('gcs/')]
    if outside:
        sys.exit('REFUSED: files added or removed outside gcs/ need a rebuild: ' + ', '.join(outside))
    if mode == 'dry':
        sys.exit(0)
    for name in sorted(changed + added, key=lambda n: n == 'gcs/index.html'):
        target = (root / name).resolve()
        assert target.is_relative_to(root), name
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + '.deploy-20261029d')
        temp.write_bytes(z.read(name))
        temp.chmod(0o755 if name.endswith('.sh') else 0o644)
        temp.replace(target)
    for name in removed:
        (root / name).unlink()
    (root / 'runtime_manifest.json').write_text(json.dumps(manifest, indent=2))
    for name, digest in files.items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
    print('SOURCE VERIFIED', len(files), 'files; changed', len(changed), '; added', len(added), '; removed', len(removed))
PY
}

if [[ ${1:-} == --dry-run ]]; then plan dry; exit 0; fi

# 0. The runtime off (the web supervisor refuses unless disarmed and recovered).
if [[ $(state | python3 -c 'import json,sys; print(json.load(sys.stdin)["runtime"])') != Stopped ]]; then
    curl -s -m 40 -X POST -H 'Content-Type: application/json' -d '{}' "$api/api/disconnect" | python3 -c \
        'import json,sys; d=json.load(sys.stdin); assert d.get("runtime")=="Stopped", d; print("runtime", d["runtime"])'
fi

# 1. Back up every installed file in the bundle, the manifest and the guides.
stamp=$(date +%Y%m%dT%H%M%S)
python3 - "$ws" "$task/before_$stamp.list" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
names = list(json.loads((root / 'runtime_manifest.json').read_text())['files']) + ['runtime_manifest.json']
Path(sys.argv[2]).write_text('\n'.join(n for n in names if (root / n).exists()) + '\n')
PY
tar -czf "$task/before_$stamp.tar.gz" -C "$ws" -T "$task/before_$stamp.list"
sha256sum "$task/before_$stamp.tar.gz" | tee "$task/backups_$stamp.sha256"

# 2. Install.
plan apply

# 3. The installed links still reach the changed sources (container paths).
for link in build/winch_ctrl/winch_ctrl build/mission_bringup/mission_bringup \
            build/mission_bringup/config/venue.yaml build/camera_ctrl/camera_ctrl; do
    target=$(readlink "$ws/$link")
    [[ -e $ws/${target#/workspace/} ]] || { echo "BROKEN LINK $link -> $target"; exit 1; }
done
echo "installed links reach src/"

# 4. Reconnect the profile that was running.
if [[ -n $profile ]]; then
    curl -s -m 60 -X POST -H 'Content-Type: application/json' -d "{\"profile_id\": \"$profile\"}" \
        "$api/api/connect" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("runtime", d.get("runtime"), d.get("connection_error") or "")'
fi
echo "$(date -Is) DEPLOY 20261029d INSTALLED, runtime restarted (no rebuild)"
