#!/bin/bash
# Venue flights one after another: for each
# "WORLD OUT TARGET", stop any idle simulator through the world maker, fly
# venue_run.sh into a fresh OUT, then grade it with sim/check_track.py.
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"
S="$(dirname "$0")"
while [ $# -ge 3 ]; do
  WORLD="$1"; OUT="$2"; TARGET="$3"; shift 3
  echo "$(date -Is) === $WORLD -> $OUT"
  curl -s -m 90 -X POST http://127.0.0.1:8777/api/sim/stop; echo
  for i in $(seq 60); do pgrep -x arducopter >/dev/null || pgrep -f '^gz sim' >/dev/null || break; sleep 2; done
  WORLD="$WORLD" bash "$S/venue_run.sh" "$OUT" > "$OUT.driver.log" 2>&1
  python3 sim/check_track.py --track "$OUT/track.csv" --layout "$OUT/layout.json" --target "$TARGET" > "$OUT/grade.txt" 2>&1
  echo "check_track exit $?" >> "$OUT/grade.txt"
  grep -a "Mission result" "$OUT.driver.log" | head -1 | cut -c1-220
  echo "$(date -Is) PASS $(grep -c '\[PASS\]' "$OUT/grade.txt") FAIL $(grep -c '\[FAIL\]' "$OUT/grade.txt") $(grep '\[FAIL\]' "$OUT/grade.txt" | tr '\n' ' ')"
done
echo "$(date -Is) all done"
