#!/usr/bin/env bash
# Harmless rehearsal of a runner that owns a separately detached child group.
set -euo pipefail
out="${1:?task-owned smoke job directory}"
setsid /usr/bin/python3 .scratch/simulation-reliability/launcher_smoke_process_20261006.py \
    --seconds 60 > "$out/escaped_child.log" 2>&1 &
child="$!"
printf '%s\n' "$child" > "$out/escaped_child_pid.txt"
cleanup() {
    kill -TERM -- "-$child" 2>/dev/null || true
    wait "$child" 2>/dev/null || true
    printf 'cleanup trap ran\n' > "$out/trap_cleanup.txt"
}
trap cleanup EXIT
/usr/bin/python3 .scratch/simulation-reliability/launcher_smoke_process_20261006.py --seconds 60
