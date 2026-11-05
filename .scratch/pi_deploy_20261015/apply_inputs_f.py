"""Apply the organiser inputs through the Pi GCS command API: dimensions, colours, six arena points."""
import json, time, urllib.request, uuid
BASE = "http://192.168.0.103:8899"
fence = [tuple(map(float, l.split(","))) for l in open("../../logs/fence6_clarified_h115.txt") if l.strip()]
dims = {"banner": {"border_m": 0.0762, "height_m": 1.15, "placement": "both", "suspended_bottom_m": 1.898, "width_m": 3.5},
        "corridor": {"length_m": 10, "nav_height_m": 2.4384, "return_side": "right", "spacing_m": 4, "wall_height_m": 3.048, "width_m": 3.5},
        "hall": {"ceiling_m": 30, "length_m": 80, "width_m": 45}, "obstacle": {"reach_frac": 0.5},
        "payload": {"length_m": 0.1, "mass_kg": 0.1, "width_m": 0.055},
        "qr": {"border_m": 0.0762, "start_m": 1, "target_m": 1}, "red_zone": {"border_m": 0.1524, "side_m": 1.524}}
cmds = [("set_arena_dimensions", {"dimensions": dims}),
        ("set_banner_colours", {"colours": {"green": "#07A03D", "orange": "#EB5A0A", "red": "#C4161C"}}),
        ("set_geofence", {"vertices": [{"lat": a, "lon": b} for a, b in fence]})]
log = open("apply_inputs_f.jsonl", "a")
for cmd, args in cmds:
    cid = f"pi-f-{cmd}-{uuid.uuid4().hex[:8]}"
    body = json.dumps({"cmd": cmd, "args": args, "command_id": cid, "confirm": True}).encode()
    req = urllib.request.Request(BASE + "/api/commands", body, {"Content-Type": "application/json"})
    res = json.loads(urllib.request.urlopen(req, timeout=20).read())
    for _ in range(30):
        time.sleep(1)
        r = json.loads(urllib.request.urlopen(f"{BASE}/api/commands/{cid}", timeout=10).read())
        if r.get("state") not in ("Submitted", "Pending", "Sent"):
            break
    print(cmd, r.get("state"), (r.get("reason") or "")[:160])
    log.write(json.dumps({"cmd": cmd, "id": cid, "res": r}) + "\n")
