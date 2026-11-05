#!/usr/bin/env bash
# Destination update 20261027b (0c241e1: the Pi drives the camera tilt servo
# on SERVO5 itself; FC SERVO5_FUNCTION 0), run as pi5 on the Pi: bundle
# pi-runtime-20261027.zip (source ac75470: GCS Camera cal and Winch cal, the
# return gate entered from its face when red ground covers every stand-off,
# COMPLETED published after a landed mission, L298N stow at its lowering
# speed, unanswered DO_WINCH judged by the measured line).
#
# The operator asked for the stale code base to go (27 Oct 2026): after a
# backup, every file under src/ (but the C1 driver, src/sllidar_ros2), scripts/
# and gcs/ that the bundle does not carry is removed, with __pycache__; the 13
# local packages' build/install trees and log/ are rebuilt from scratch (the
# driver's are kept); crash dumps are moved out of the workspace, not deleted.
# Kept as they are: /home/pi5/.aerothon (measured state), the measured
# runtime.env, the profiles in ~/.local/state/aerothon. No root, no arming.
#
#   bash deploy_pi.sh --list-stale    print what would be removed; change nothing
#   bash deploy_pi.sh                 disconnect the runtime, back up, install
set -euo pipefail
ws=/home/pi5/aerothon_ws
dep=/home/pi5/aerothon-deploy
task=/home/pi5/.local/state/aerothon/deploy_20261027b
archive=$task/pi-runtime-20261027.zip
want=9760de8294e93bcaad4b28fc37676160c1034e1320990e5275b7a8d690391046
echo "$want  $archive" | sha256sum -c -

sweep() {   # $1 = list | apply
python3 - "$archive" "$ws" "$1" <<'PY'
import hashlib, json, os, shutil, sys, zipfile
from pathlib import Path
archive, root, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
with zipfile.ZipFile(archive) as z:
    manifest = json.loads(z.read('runtime_manifest.json'))
    files = manifest['files']
    keep = set(files) | {'runtime_manifest.json'}
    stale, caches = [], []
    for top in ('src', 'scripts', 'gcs'):
        for dirpath, dirnames, filenames in os.walk(root / top):
            rel_dir = Path(dirpath).relative_to(root)
            if rel_dir.parts[:2] == ('src', 'sllidar_ros2'):
                dirnames[:] = []
                continue
            for d in list(dirnames):
                if d == '__pycache__':
                    caches.append(str(rel_dir / d))
                    dirnames.remove(d)
            for f in filenames:
                rel = str(rel_dir / f)
                if rel not in keep:
                    stale.append(rel)
    for f in os.listdir(root):
        if (root / f).is_file() and f not in keep and not f.startswith('core.') and not f.startswith('.lgd-'):
            stale.append(f)
    print(f'{len(stale)} stale file(s), {len(caches)} __pycache__ dir(s) not in the bundle:')
    for name in sorted(stale):
        print('  stale', name)
    if mode == 'list':
        sys.exit(0)
    changed = []
    for name in sorted(files, key=lambda n: n == 'gcs/index.html'):   # index.html last
        data = z.read(name)
        assert hashlib.sha256(data).hexdigest() == files[name], name
        target = (root / name).resolve()
        assert target.is_relative_to(root), name
        if not target.exists() or target.read_bytes() != data:
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_name(target.name + '.deploy-20261027')
            temp.write_bytes(data)
            temp.chmod(0o755 if name.endswith('.sh') else 0o644)
            temp.replace(target)
            changed.append(name)
    (root / 'runtime_manifest.json').write_text(json.dumps(manifest, indent=2))
    for name in stale:
        (root / name).unlink()
    for name in caches:
        shutil.rmtree(root / name, ignore_errors=True)
    for top in ('src', 'scripts', 'gcs'):                    # emptied directories
        for dirpath, dirnames, filenames in sorted(os.walk(root / top), reverse=True):
            p = Path(dirpath)
            if p != root / top and not any(p.iterdir()) and 'sllidar_ros2' not in p.parts:
                p.rmdir()
    for name, digest in files.items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
    print('SOURCE VERIFIED', len(files), 'files; changed', len(changed), '; removed', len(stale), 'stale')
    for name in changed:
        print('  changed', name)
    Path(sys.argv[2], '.local_ros_packages').write_text(' '.join(manifest['local_ros_packages']))
PY
}

if [[ ${1:-} == --list-stale ]]; then
    sweep list
    ls -la "$ws"/core.* 2>/dev/null | sed 's/^/  crash dump (moved out on install): /' || true
    exit 0
fi

# 0. The runtime off. The web supervisor refuses unless disarmed and recovered.
curl -s -m 40 -X POST -H 'Content-Type: application/json' -d '{}' \
    http://127.0.0.1:8899/api/disconnect | python3 -c \
    'import json,sys; d=json.load(sys.stdin); assert d.get("runtime")=="Stopped", d; print("runtime", d["runtime"])'

# 1. Back up everything this replaces or removes.
stamp=$(date +%Y%m%dT%H%M%S)
tar -czf "$task/before_$stamp.tar.gz" -C "$ws" --exclude=src/sllidar_ros2 \
    src scripts gcs runtime_manifest.json AGENTS.md MASTER_DOCUMENTATION.md
tar -czf "$task/deploy_before_$stamp.tar.gz" -C /home/pi5 aerothon-deploy
sha256sum "$task"/*_"$stamp".tar.gz > "$task/backups_$stamp.sha256"
cat "$task/backups_$stamp.sha256"

# 2. Install the bundle, remove what it does not carry.
sweep apply

# 3. Crash dumps out of the workspace (kept, not deleted).
mkdir -p "$task/crash_dumps"
for f in "$ws"/core.*; do [[ -e $f ]] && mv "$f" "$task/crash_dumps/" && echo "moved $(basename "$f") to $task/crash_dumps"; done

# 4. pi5-owned launchers; the measured runtime.env keeps everything but the
# winch backend, which stays the L298N.
for file in run_container.sh run_router.sh console.launch.py Dockerfile Dockerfile.dependencies profile_router.py stop_runtime.py; do
    if ! cmp -s "$ws/scripts/pi_runtime/$file" "$dep/$file"; then
        install -m "$([[ $file == *.sh ]] && echo 0755 || echo 0644)" "$ws/scripts/pi_runtime/$file" "$dep/$file"
        echo "deploy updated: $file"
    fi
done
cp -p "$dep/runtime.env" "$task/runtime.env.before_$stamp"
grep -q '^AEROTHON_WINCH_BACKEND=l298n$' "$dep/runtime.env" || {
    sed -i '/^AEROTHON_WINCH_BACKEND=/d' "$dep/runtime.env"
    echo 'AEROTHON_WINCH_BACKEND=l298n' >> "$dep/runtime.env"; }
diff "$task/runtime.env.before_$stamp" "$dep/runtime.env" || true

# 5. Clean rebuild of the local packages inside the runtime image, on one
# core (full-load builds reset this Pi on its supply, 25 Oct).
pkgs=$(cat "$ws/.local_ros_packages")
for p in $pkgs; do rm -rf "$ws/build/$p" "$ws/install/$p"; done
rm -rf "$ws/log"
image=$(grep -hE '^AEROTHON_IMAGE=' "$dep/runtime.env" "$ws/scripts/pi_runtime/runtime.env" | head -1 | cut -d= -f2)
[[ -n $image ]] || { echo "no AEROTHON_IMAGE in runtime.env"; exit 1; }
docker run --rm --cpus 1 --user 1000:1000 --network none \
    --mount "type=bind,src=$ws,dst=/workspace" "$image" /bin/bash -c \
    'source /opt/ros/jazzy/setup.bash && cd /workspace && colcon build --symlink-install --parallel-workers 1 2>&1 | tail -25'
echo "$(date -Is) DEPLOY 20261027 FILES AND BUILD COMPLETE"
