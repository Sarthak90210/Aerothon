"""Wait for the GCS flight-readiness interlock, then Start the mission as the operator does."""
import json
import time
import urllib.request
import uuid

HOST = "http://127.0.0.1:8899"


def call(path, data=None, timeout=60):
    req = urllib.request.Request(HOST + path, method="POST" if data is not None else "GET",
                                 data=None if data is None else json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


for i in range(120):
    c = call("/api/check")
    if c.get("flight_ready"):
        break
    if i % 10 == 0:
        print("not ready:", [it for it in c.get("items", []) if not it.get("ok", True)][:4], flush=True)
    time.sleep(5)
else:
    raise SystemExit("flight readiness never came up")
print("flight_ready", flush=True)
time.sleep(5)
cid = str(uuid.uuid4())
r = call("/api/commands", {"command_id": cid, "cmd": "start", "confirm": True,
                           "args": {"task": "mission", "params": {"height": 5.0, "target": "", "waypoints": []}}})
print("start:", json.dumps(r)[:300], flush=True)
for _ in range(30):
    r = call(f"/api/commands/{cid}")
    if r.get("state") not in ("Submitted", "Pending", "Sent"):
        break
    time.sleep(2)
if r.get("state") == "Accepted":
    # Accepted by the web host is not running: the execution layer may still
    # refuse it (a momentary actuator-feedback lapse). Report what it did.
    for _ in range(15):
        time.sleep(2)
        ex = call("/api/state").get("execution") or {}
        if ex.get("command_id") == cid and ex.get("state") not in ("Submitted", "Accepted", "Pending"):
            r = {"command_id": cid, "state": "Running" if ex["state"] == "Running" else ex["state"],
                 "reason": ex.get("reason", ""), "stage": ex.get("stage")}
            break
print("start outcome:", json.dumps(r)[:300], flush=True)
