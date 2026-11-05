#!/usr/bin/env bash
# Destination update, run as pi5 on the Pi: bundle logs/pi-runtime-20261025.zip
# (source 560da40 + working tree of 25 Oct 2026: red-zone delivery-zone filter,
# return-slot fixes, L298N winch + RC ch5, SERVO5 camera).
# Verifies the archive, backs up what it replaces, installs every manifest file
# with its digest checked, refreshes the pi5-owned launchers, switches the
# measured runtime.env to the L298N winch (nothing else in it changes) and
# rebuilds the workspace inside the runtime image. No root, no arming; the
# runtime is restarted separately, disarmed, through the GCS.
set -euo pipefail
ws=/home/pi5/aerothon_ws
dep=/home/pi5/aerothon-deploy
task=/home/pi5/.local/state/aerothon/deploy_20261025
# 20261026b (ac75470): GCS Camera cal and Winch cal (camera_tilt.json and
# winch_limits.json in /home/pi5/.aerothon), the return gate entered from
# its face when red ground covers every stand-off, COMPLETED published
# after a landed mission, L298N stow at its lowering speed.
# 20261026: the organisers' field PDF (blue exit banner role, borderless QR,
# 6 ft exit-lane boards, GCS preset); RC6 hand drive and earlier fixes kept.
# 20261025e: hand drive moves to RC6, the three-position switch (channel 5
# is two-position on this transmitter); GCS label and FC notes follow.
# 20261025d: channel-5 hand drive waits for the switch in the middle after
# startup, a mission or a lost radio (a switch left at LOW lowered at boot);
# it also replaces the Pi-local rc_manual_channel 0 hold in venue.yaml.
# 20261025c added the RC bridge (/aerothon/rc/in from RC_CHANNELS even with
# chancount 0) and the measured lowering direction -1. 20261025b added the
# test-option fixes (winch limit window, stow done only
# with the line in, pilot floor margin, height hold blended toward FCU z).
archive=$task/pi-runtime-20261026b.zip
want=1b000092c5995d02d6854a41c8c8be20a565e1fd858037e6816d3c32f6ca45d3
echo "$want  $archive" | sha256sum -c -

# 1. Back up what this replaces (the lidar driver and build trees are kept).
stamp=$(date +%Y%m%dT%H%M%S)
tar -czf "$task/before_$stamp.tar.gz" -C "$ws" --exclude=src/sllidar_ros2 \
    src scripts gcs runtime_manifest.json AGENTS.md MASTER_DOCUMENTATION.md
[[ -d $dep ]] && tar -czf "$task/deploy_before_$stamp.tar.gz" -C /home/pi5 aerothon-deploy
sha256sum "$task"/*_"$stamp".tar.gz > "$task/backups_$stamp.sha256"

# 2. Install every manifest file, digest-checked, atomically per file.
python3 - "$archive" "$ws" <<'PY'
import hashlib, json, sys, zipfile
from pathlib import Path
archive, root = Path(sys.argv[1]), Path(sys.argv[2])
old = json.loads((root / 'runtime_manifest.json').read_text())['files'] if (root / 'runtime_manifest.json').exists() else {}
changed = []
with zipfile.ZipFile(archive) as z:
    manifest = json.loads(z.read('runtime_manifest.json'))
    for name in sorted(manifest['files'], key=lambda n: n == 'gcs/index.html'):   # index.html last
        data = z.read(name)
        assert hashlib.sha256(data).hexdigest() == manifest['files'][name], name
        target = (root / name).resolve()
        assert target.is_relative_to(root), name
        if not target.exists() or target.read_bytes() != data:
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_name(target.name + '.deploy-20261025')
            temp.write_bytes(data)
            temp.chmod(0o755 if name.endswith('.sh') else 0o644)
            temp.replace(target)
            changed.append(name)
(root / 'runtime_manifest.json').write_text(json.dumps(manifest, indent=2))
for name, digest in manifest['files'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
stale = sorted(set(old) - set(manifest['files']))
print('SOURCE VERIFIED', len(manifest['files']), 'files; changed', len(changed))
for name in changed:
    print('  changed', name)
for name in stale:
    print('  no longer in the bundle (left in place):', name)
PY

# 3. pi5-owned launchers in aerothon-deploy (install_services.sh's list).
# On a fresh install the directory does not exist until root runs
# install_services.sh, which copies these and the bundle's runtime.env.
if [[ -d $dep ]]; then
for file in run_container.sh run_router.sh console.launch.py Dockerfile Dockerfile.dependencies profile_router.py stop_runtime.py; do
    if ! cmp -s "$ws/scripts/pi_runtime/$file" "$dep/$file"; then
        install -m "$([[ $file == *.sh ]] && echo 0755 || echo 0644)" "$ws/scripts/pi_runtime/$file" "$dep/$file"
        echo "deploy updated: $file"
    fi
done

# 4. Measured runtime.env: only the winch backend changes (operator, 24 Oct 2026).
cp -p "$dep/runtime.env" "$task/runtime.env.before_$stamp"
if grep -q '^AEROTHON_WINCH_BACKEND=' "$dep/runtime.env"; then
    sed -i 's/^AEROTHON_WINCH_BACKEND=.*/AEROTHON_WINCH_BACKEND=l298n/' "$dep/runtime.env"
else
    printf '# Pi L298N payload motor (ENA BCM18, IN1 BCM23, IN2 BCM24); RC ch5 by hand when no mission runs.\nAEROTHON_WINCH_BACKEND=l298n\n' >> "$dep/runtime.env"
fi
diff "$task/runtime.env.before_$stamp" "$dep/runtime.env" || true
grep -E '^AEROTHON_(FCU_DEVICE|FCU_BAUD|WINCH_BACKEND|IMAGE)=' "$dep/runtime.env"
else
    echo "no $dep yet: root's install_services.sh installs the launchers and runtime.env"
fi

# 5. Rebuild inside the runtime image, as the runtime's own user, on one core:
# full-load builds reset this Pi on its current supply (25 Oct).
image=$(grep -E '^AEROTHON_IMAGE=' "$ws/scripts/pi_runtime/runtime.env" | cut -d= -f2)
docker run --rm --cpus 1 --user 1000:1000 --network none \
    --mount "type=bind,src=$ws,dst=/workspace" "$image" /bin/bash -c \
    'source /opt/ros/jazzy/setup.bash && cd /workspace && colcon build --symlink-install --parallel-workers 1 2>&1 | tail -25'
echo "$(date -Is) DEPLOY 20261025 FILES AND BUILD COMPLETE"
