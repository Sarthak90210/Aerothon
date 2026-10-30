"""Return-lane trace of a headless run: track in the lane frame, controller detail, lidar gaps.

    python3 lane_trace.py RUN_DIR [t0 t1]
"""
import csv, json, math, sys
run = sys.argv[1]
L = json.load(open(f"{run}/layout.json"))
x0, y0, yaw, length, width, h = L["corridors"]["return"]
c, s = math.cos(yaw), math.sin(yaw)
def uv(x, y):
    dx, dy = x - x0, y - y0
    return dx * c + dy * s, -dx * s + dy * c
for o in L["obstacles"]:
    us = [uv(*p) for p in o["poly"]]
    print("board u %.2f v %.2f..%.2f" % (sum(u for u, _ in us) / 4, min(v for _, v in us), max(v for _, v in us)))
hx, hy = L.get("home_world", [0, 0])
rows = list(csv.DictReader(open(f"{run}/track.csv")))
inside = [r for r in rows if -0.5 <= uv(float(r["x"]) + hx, float(r["y"]) + hy)[0] <= 6.5
          and abs(uv(float(r["x"]) + hx, float(r["y"]) + hy)[1]) < 2 and r["state"] == "RETURN_CORRIDOR"]
t0 = float(sys.argv[2]) if len(sys.argv) > 2 else (float(inside[0]["t_sim"]) - 1 if inside else 0)
t1 = float(sys.argv[3]) if len(sys.argv) > 3 else t0 + 14
det = {}
for line in open(f"{run}/onboard.jsonl"):
    d = json.loads(line)
    if "avoidance" in d:
        a = d["avoidance"]; a = a.get("data", a)
        det[round(float(d["stamp"]), 1)] = a
scans = []
for line in open(f"{run}/onboard_lidar.jsonl"):
    d = json.loads(line)
    if d.get("received_stamp") is not None:
        scans.append(float(d["received_stamp"]))
gaps = [(round(a, 2), round(b - a, 2)) for a, b in zip(scans, scans[1:]) if b - a > 0.3 and t0 <= a <= t1]
print("scan gaps >0.3 s in window:", gaps)
for r in rows:
    t = float(r["t_sim"])
    if t0 <= t <= t1 and abs(t * 2 - round(t * 2)) < 0.06:
        u, v = uv(float(r["x"]) + hx, float(r["y"]) + hy)
        a = det.get(round(t, 1)) or {}
        print(f"t={t:6.1f} u={u:5.2f} v={v:5.2f} {r['state'][:16]:16s} {a.get('state','')} front={a.get('front_m')} "
              f"L={a.get('side_left_m')} R={a.get('side_right_m')} gap={a.get('gap_bearing_deg')} vx={a.get('cmd_vx')} vy={a.get('cmd_vy_left')} yr={a.get('cmd_yaw_rate')}")
