"""Enter the field PDF's organiser inputs through the GCS web host, as the operator does.

    python3 apply_field_inputs.py WORLD

Arena dimensions: the GCS built-in preset "AeroTHON 2026 Track 1 field
(organiser PDF)" when the world was built from it unchanged; otherwise the
world's values saved as an operator preset "Field PDF: WORLD" and that applied.
Then the banner colours (green / exit / red) and the geofence from the world
maker's organiser endpoint. Waits for the mission's APPLIED confirmation.
"""
import json
import os
import sys
import time
import urllib.request
import uuid

HOST = "http://127.0.0.1:8899"
WM = "http://127.0.0.1:8777"
PRESET = "AeroTHON 2026 Track 1 field (organiser PDF)"
ROOT = "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"
world = sys.argv[1]


def get(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def command(cmd, args):
    for attempt in range(5):
        cid = str(uuid.uuid4())
        req = urllib.request.Request(f"{HOST}/api/commands", method="POST",
                                     data=json.dumps({"command_id": cid, "cmd": cmd, "args": args,
                                                      "confirm": True}).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=30).read()
        except Exception as error:                       # noqa: BLE001 - retried
            print(f"{cmd}: post failed ({error}); retry {attempt + 1}", flush=True)
            time.sleep(5)
            continue
        for _ in range(60):
            r = get(f"{HOST}/api/commands/{cid}")
            if r["state"] not in ("Submitted", "Pending", "Sent"):
                print(f"{cmd}: {r['state']} {r.get('reason', '')}", flush=True)
                return r
            time.sleep(1)
    raise SystemExit(f"{cmd}: no outcome")


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


for _ in range(120):                       # fresh runtime telemetry
    s = get(f"{HOST}/api/state")
    if s.get("fresh"):
        break
    time.sleep(3)
print("runtime fresh:", s.get("fresh"), flush=True)
time.sleep(10)
spec = json.load(open(os.path.join(ROOT, "sim/worlds", f"{world}.json")))
# The GCS lists the built-in presets from this same schema (arena_dimensions).
sys.path.insert(0, os.path.join(ROOT, "src/aerothon_mission/mission_bt"))
from mission_bt import arena_dimensions as A               # noqa: E402
builtin = A.validate(A.BUILTIN_PRESETS[PRESET])
if same(builtin, A.validate(spec["dimensions"])):
    name, dims = PRESET, A.BUILTIN_PRESETS[PRESET]
    print("using the built-in preset", name, flush=True)
else:
    name, dims = f"Field PDF: {world}", spec["dimensions"]
    command("save_dimension_preset", {"name": name, "dimensions": dims})
    print("saved operator preset", name, flush=True)
RUNTIME_LOG = os.path.expanduser("~/.local/state/aerothon-world-sim/runtime.log")
with open(RUNTIME_LOG, "rb") as f:
    seen = sum(1 for _ in f)
command("set_arena_dimensions", {"dimensions": dims})
# The mission's own confirmation (mission_bt logs what it applied).
for _ in range(60):
    with open(RUNTIME_LOG, "rb") as f:
        new = f.read().decode("utf-8", "replace").splitlines()[seen:]
    hit = [l for l in new if "arena dimensions applied" in l]
    if hit:
        print("APPLIED:", hit[-1].split("applied:", 1)[1][:240], flush=True)
        break
    time.sleep(2)
else:
    print("arena dimensions NOT applied within 120 s", flush=True)
org = get(f"{WM}/api/organiser/{world}", timeout=90)
print("banner colours", org["banner_colours"], flush=True)
command("set_banner_colours", {"colours": org["banner_colours"]})
verts = [dict(zip(("lat", "lon"), map(float, line.split(",")))) for line in org["geofence"].splitlines()]
command("set_geofence", {"vertices": verts})
print("home", org["home"], "fence points", len(verts), flush=True)
