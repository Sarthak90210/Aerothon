#!/usr/bin/env bash
# Destination update 20261029, run as pi5 on the Pi: bundle
# pi-runtime-20261029.zip (source ff927f5). GCS only: a calibration window's
# reviewed command (Camera cal Apply/Clear, Lidar cal Apply, Winch cal
# paid-out limit, Arena preset Delete) is confirmed in a dialog over that
# window, labelled with what it applies (28 Oct: Camera cal recorded, the
# Confirm box sat in the Mission panel unseen, nothing applied).
#
# Against the installed 0c241e1 bundle only gcs/ and MASTER_DOCUMENTATION.md
# differ, and web_host serves /workspace/gcs directly. So unlike 20261027b
# this install does NOT stop the runtime and does NOT rebuild: the runtime,
# its Camera cal draft and the FC link stay as they are, and the full-load
# build that resets this Pi on its supply is not needed. It refuses if any
# file outside gcs/ or the two guides would change (that needs the full
# route, deploy_20261027b). Old hashed GCS assets the bundle does not carry
# are removed after a backup; nothing else is removed. No root, no arming.
#
#   bash deploy_pi_d.sh --dry-run    verify and print what would change
#   bash deploy_pi_d.sh              back up and install
set -euo pipefail
ws=/home/pi5/aerothon_ws
task=/home/pi5/.local/state/aerothon/deploy_20261029
archive=$task/pi-runtime-20261029.zip
want=69f05acde731e69ccf58d3bf5528df02d3bd8f8674049e133ae8f08ef2e7dba4
echo "$want  $archive" | sha256sum -c -

# 0. No task running and, with a runtime up, a confirmed disarm or no control.
curl -s -m 10 http://127.0.0.1:8899/api/state | python3 -c '
import json, sys
s = json.load(sys.stdin)
e = s.get("execution") or {}
active = bool(e) and e.get("state") not in {"Completed", "Failed", "Outcome unknown"}
print("runtime", s["runtime"], "| fresh", s["fresh"], "| can_disconnect", s["can_disconnect"], "| execution", e.get("state"))
assert not active, "a task is running: finish it first"
assert s["runtime"] == "Stopped" or s["can_disconnect"], "runtime up without a confirmed disarm"'

install() {   # $1 = dry | apply
python3 - "$archive" "$ws" "$1" <<'PY'
import hashlib, json, sys, zipfile
from pathlib import Path
archive, root, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
with zipfile.ZipFile(archive) as z:
    manifest = json.loads(z.read('runtime_manifest.json'))
    files = manifest['files']
    changed = []
    for name, digest in files.items():
        data = z.read(name)
        assert hashlib.sha256(data).hexdigest() == digest, name
        target = root / name
        if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            changed.append(name)
    outside = [n for n in changed if not n.startswith('gcs/') and n not in ('MASTER_DOCUMENTATION.md', 'AGENTS.md')]
    stale = sorted(str(p.relative_to(root)) for p in (root / 'gcs').rglob('*')
                   if p.is_file() and str(p.relative_to(root)) not in files)
    print(len(changed), 'file(s) to change:'); [print('  change', n) for n in sorted(changed)]
    print(len(stale), 'stale GCS file(s):'); [print('  stale', n) for n in stale]
    if outside:
        sys.exit('REFUSED: files outside gcs/ and the guides differ (use the full route): ' + ', '.join(outside))
    if mode == 'dry':
        sys.exit(0)
    for name in sorted(changed, key=lambda n: n == 'gcs/index.html'):   # index.html last
        target = (root / name).resolve()
        assert target.is_relative_to(root), name
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + '.deploy-20261029')
        temp.write_bytes(z.read(name))
        temp.chmod(0o644)
        temp.replace(target)
    (root / 'runtime_manifest.json').write_text(json.dumps(manifest, indent=2))
    for name in stale:
        (root / name).unlink()
    for name, digest in files.items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
    print('SOURCE VERIFIED', len(files), 'files; changed', len(changed), '; removed', len(stale), 'stale GCS')
PY
}

if [[ ${1:-} == --dry-run ]]; then install dry; exit 0; fi

# 1. Back up what this replaces or removes.
stamp=$(date +%Y%m%dT%H%M%S)
tar -czf "$task/before_$stamp.tar.gz" -C "$ws" gcs runtime_manifest.json AGENTS.md MASTER_DOCUMENTATION.md
sha256sum "$task/before_$stamp.tar.gz" | tee "$task/backups_$stamp.sha256"

# 2. Install.
install apply
echo "$(date -Is) DEPLOY 20261029 GCS INSTALLED (runtime not restarted, no rebuild)"
