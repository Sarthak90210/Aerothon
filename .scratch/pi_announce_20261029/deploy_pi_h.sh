#!/usr/bin/env bash
# Destination update 20261029e, run as pi5 on the Pi: bundle
# pi-runtime-20261029e.zip (source 4ee62a8). The router announces the Pi in
# Mission Planner's Messages tab ("Pi booted", "Pi Wi-Fi up"). Only
# scripts/mav_router.py and the guide change; the runtime is NOT restarted
# (a web-API restart left two runtimes driving the winch pins, 29 Oct). The
# router picks the new file up when it restarts: its supervisor relaunches it.
#
#   bash deploy_pi_h.sh --dry-run    verify and print what would change
#   bash deploy_pi_h.sh              back up and install
set -euo pipefail
ws=/home/pi5/aerothon_ws
task=/home/pi5/.local/state/aerothon/deploy_20261029e
archive=$task/pi-runtime-20261029e.zip
want=7146a03b0066e0aa27d1f1245d389e64cf0bb6c9df4a854fbdf3a4bf524a526f
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
    allowed = {'MASTER_DOCUMENTATION.md', 'scripts/mav_router.py'}
    outside = [n for n in added + removed + changed if n not in allowed]
    if outside:
        sys.exit('REFUSED: this router-only install would change: ' + ', '.join(outside))
    if mode == 'dry':
        sys.exit(0)
    for name in sorted(changed + added, key=lambda n: n == 'gcs/index.html'):
        target = (root / name).resolve()
        assert target.is_relative_to(root), name
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + '.deploy-20261029e')
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

echo "$(date -Is) DEPLOY 20261029e ROUTER INSTALLED (runtime not restarted)"
