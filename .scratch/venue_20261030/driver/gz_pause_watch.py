"""Evaluation harness: log Gazebo pause/stall transitions into OUT/gz_pause.log and
resume a paused world (the operator's Play button). Nothing here reaches the flight
stack. Runs until STOP_FILE exists.

    gz_pause_watch.py OUT STOP_FILE
"""
import json
import sys
import threading
import time
from pathlib import Path

from gz.msgs10.boolean_pb2 import Boolean
from gz.msgs10.world_control_pb2 import WorldControl
from gz.msgs10.world_stats_pb2 import WorldStatistics
from gz.transport13 import Node

out, stop = Path(sys.argv[1]), Path(sys.argv[2])
log = open(out / "gz_pause.log", "a")
lock = threading.Lock()
st = {"paused": None, "iterations": None, "sim_s": None, "wall": 0.0, "silent": False}


def note(**d):
    log.write(json.dumps({"wall": round(time.time(), 3), **d}) + "\n")
    log.flush()


def on_stats(m):
    with lock:
        st["iterations"] = m.iterations
        st["sim_s"] = round(m.sim_time.sec + m.sim_time.nsec * 1e-9, 3)
        st["wall"] = time.time()
        if st["silent"]:
            note(event="stats_resumed", iterations=m.iterations, sim_s=st["sim_s"])
            st["silent"] = False
        if m.paused != st["paused"]:
            note(event="paused" if m.paused else "running", iterations=m.iterations, sim_s=st["sim_s"])
            st["paused"] = m.paused


node = Node()
if not node.subscribe(WorldStatistics, "/world/mission2/stats", on_stats):
    raise SystemExit("stats subscription failed")
note(event="watch_started")
while not stop.exists():
    time.sleep(1.0)
    with lock:
        paused, it, last = st["paused"], st["iterations"], st["wall"]
        if last and time.time() - last > 5 and not st["silent"]:
            st["silent"] = True
            note(event="stats_silent", iterations=it, sim_s=st["sim_s"])
    if paused:
        ok, res = node.request("/world/mission2/control", WorldControl(pause=False),
                               WorldControl, Boolean, 3000)
        note(event="resume_requested", ok=bool(ok and res.data), iterations=it)
        time.sleep(2.0)
note(event="watch_stopped")
