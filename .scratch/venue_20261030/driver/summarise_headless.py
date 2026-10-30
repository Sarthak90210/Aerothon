"""One line per headless venue run: navigation checks, clearances, target match.

    python3 summarise_headless.py logs/venue_20261030/headless_b
"""
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
rows = []
for run in sorted(p for p in root.iterdir() if p.is_dir()):
    g = run / "navigation_grade.json"
    log = (run / "stack.log").read_text(errors="replace") if (run / "stack.log").exists() else ""
    spec = json.loads((run / "world_spec.json").read_text()) if (run / "world_spec.json").exists() else {}
    target = spec.get("start_target", "?")
    tid = (spec.get("qr", {}).get("ids") or {}).get(target)
    result = re.findall(r"Mission result: (\w+)", log)
    matched = bool(re.search(r"(target|marker)[^\n]{0,80}(matched|MATCH)", log, re.I))
    if not g.exists():
        rows.append(f"{run.name:42s} NO GRADE  result={result[-1] if result else '?'}")
        continue
    sp = [float(json.loads(l)["stamp"]) for l in open(run / "flight_commands.jsonl")
          if '"/mavros/setpoint_raw/local"' in l] if (run / "flight_commands.jsonl").exists() else []
    gaps = [b - a for a, b in zip(sp, sp[1:]) if b - a < 5.0]
    starved = sum(1 for x in gaps if x > 0.3)
    d = json.loads(g.read_text())
    f = d["full_grade"]
    bad = [k for k, v in d["checks"].items() if not v]
    rows.append(f"{run.name:42s} nav={'PASS' if d['pass_navigation'] else 'FAIL'} "
                f"red={d['measured_red_clearance_m'] or 0:.2f} corr={d['measured_corridor_clearance_m'] or 0:.2f} "
                f"t={f['flight_time_s']:.0f}s land={f['landed_from_home_m']} target={target}/{tid} "
                f"setpoint gaps>0.3s={starved} result={result[-1] if result else '?'} {'FAILED: ' + '; '.join(bad) if bad else ''}")
print("\n".join(rows))
