#!/usr/bin/env python3
"""Serve the world editor, keep its worlds, and fly them.

    python3 tools/world_editor/serve.py            # http://127.0.0.1:8777/

Run it inside WSL (the simulator lives there); the Windows browser reaches it
at the same address. Standard library only.

    GET  /                      the editor
    GET  /api/worlds            saved worlds (sim/worlds/*.json)
    GET  /api/worlds/NAME       one world
    POST /api/worlds/NAME       save (validated; refused worlds are still saved
                                and reported, so work is never lost)
    POST /api/validate          errors and warnings from scripts/world_spec.py
    POST /api/run/NAME?gui=1&record=1
                                fly NAME with scripts/run_custom_world.sh
    GET  /api/run               the run in progress, or the last one

The arena dimensions are the GCS's own fields (mission_bt.arena_dimensions).
Saving a world that carries them also saves them as the GCS preset
"World NAME", so the operator loads and applies in the GCS exactly what the
world was built from:

    GET  /api/dimensions        the GCS fields and presets
    POST /api/apply_dimensions  {spec, dimensions} -> the world rebuilt to them
    POST /api/sim/start/NAME    the laptop-simulation route for NAME: Gazebo,
                                SITL and the sensor gateway, plus the real web
                                host serving the GCS on :8899. Nothing connects,
                                arms or starts: the operator Connects (starting
                                the production runtime), applies the preset,
                                enters the organiser inputs and starts the
                                mission from the GCS
    GET  /api/sim               that simulator's state
    POST /api/sim/stop          stop it (refused while the aircraft is armed)
    GET  /api/organiser/NAME    the geofence and banner colours to type into
                                the GCS, georeferenced on the FCU home
    GET  /api/home              the FCU home alone (the editor converts each
                                geofence point it shows)
"""

import argparse
import asyncio
import importlib
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
# The simulated airframe's venue parameters: venue.yaml plus what was
# MEASURED on the simulated airframe (search braking) and the simulation's
# chosen cruise. The aircraft keeps mission_bringup/config/venue.yaml.
SIM_VENUE = ROOT / "src/aerothon_sim/sim_gazebo/config/world_sim_venue.yaml"
WORLDS = ROOT / "sim" / "worlds"
LOGS = ROOT / "logs" / "custom"
sys.path.insert(0, str(ROOT / "scripts"))
import world_spec  # noqa: E402

NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
LIVE_LOG = Path("/tmp/aerothon_live_mission.log")
RUN = {"proc": None, "name": "", "started": 0.0}
# The aggregator's default preset store (dimension_presets_file).
PRESETS = Path(os.path.expanduser("~/.aerothon/dimension_presets.json"))
# The laptop-simulation route (master guide section 4): this host runs
# Gazebo, SITL and the sensor gateway; the real web host serves the GCS and,
# on the operator's Connect, starts the production runtime against them.
SIM = {"proc": None, "web": None, "name": "", "preset": "", "started": 0.0}
GCS_PORT = 8899
GCS_URL = f"http://127.0.0.1:{GCS_PORT}/"
AGGREGATOR_WS = "ws://127.0.0.1:8765"
WEB_STATE = Path(os.path.expanduser("~/.local/state/aerothon-world-sim"))
PROFILE_ID = "world_sim"
SIM_RECORD = WEB_STATE / "world-sim.json"
RUNTIME_DOMAIN = "42"                  # the production runtime's ROS domain
GATEWAY_PYTHON = ROOT / ".scratch/pi_remote_runtime_20261014/testenv/bin/python"
OFFLINE_TILES = ROOT / ".scratch/india_map_20261018/tiles"
SIM_DELIVERY_PROFILE = ROOT / "logs/delivery_profile_20261005.json"
SIM_DELIVERY_NAME = "sim_delivery_profile_20261005.json"
ROS_ENV = ("source /opt/ros/jazzy/setup.bash && "
           "{ [ ! -f install/setup.bash ] || source install/setup.bash; } && ")


def preset_name(world):
    return f"World {world}"


def save_gcs_preset(name, dims):
    """Write ``dims`` into the GCS preset store under ``name``, atomically and
    leaving every other preset as it was."""
    A = world_spec.arena_dimensions()
    dims = A.validate(dims)
    if name in A.BUILTIN_PRESETS:
        raise ValueError(f"{name!r} is a built-in GCS preset")
    presets = {}
    if PRESETS.exists():
        presets = json.loads(PRESETS.read_text(encoding="utf-8") or "{}")
    presets[name] = dims
    PRESETS.parent.mkdir(parents=True, exist_ok=True)
    tmp = PRESETS.with_suffix(".tmp")
    tmp.write_text(json.dumps(presets, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, PRESETS)
    return name


def dimension_catalogue():
    A = world_spec.arena_dimensions()
    saved = {}
    if PRESETS.exists():
        for name, dims in json.loads(PRESETS.read_text(encoding="utf-8") or "{}").items():
            try:
                saved[name] = A.validate(dims)
            except (ValueError, TypeError, AttributeError):
                pass
    return {"fields": [{"group": g, "key": k, "label": label, "default": default,
                        "min": lo, "max": hi, "used_by": used}
                       for g, k, label, default, lo, hi, used in A.FIELDS],
            "placements": list(A.PLACEMENTS), "return_sides": list(A.RETURN_SIDES),
            "presets": {"builtin": {k: A.validate(v) for k, v in A.BUILTIN_PRESETS.items()},
                        "saved": saved}}


def simulator_running():
    """Any simulator on this host, ours or not (one at a time)."""
    return subprocess.run(["pgrep", "-f", "[a]rducopter|[g]z sim"],
                          capture_output=True).returncode == 0


def port_open(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False


def aircraft_armed(timeout=4.0):
    """True/False from the GCS aggregator's telemetry; None when unknown."""
    try:
        import websockets
    except ImportError:
        return None

    async def read():
        async with websockets.connect(AGGREGATOR_WS, max_size=None, open_timeout=2) as ws:
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                msg = json.loads(await asyncio.wait_for(ws.recv(), end - time.monotonic()))
                if msg.get("kind") == "telemetry":
                    armed = ((msg.get("data") or {}).get("mission") or {}).get("armed")
                    if armed is not None:
                        return bool(armed)
        return None

    try:
        return asyncio.run(read())
    except Exception:  # noqa: BLE001 - unreachable aggregator: unknown
        return None


def pgid_of(handle):
    """A started Popen (its own session) or an adopted process-group id."""
    return handle if isinstance(handle, int) else handle.pid


def alive(handle):
    """Any member of the group still running (gz server and arducopter
    outlive the launcher). A Popen is reaped first so a zombie leader does
    not count."""
    if handle is None:
        return False
    if not isinstance(handle, int):
        handle.poll()
    try:
        os.killpg(pgid_of(handle), 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def remember_sim():
    """Record the simulator's groups so a restarted editor can still stop it."""
    WEB_STATE.mkdir(parents=True, exist_ok=True)
    SIM_RECORD.write_text(json.dumps({
        "name": SIM["name"], "preset": SIM["preset"], "started": SIM["started"],
        "sim_pgid": pgid_of(SIM["proc"]), "web_pgid": pgid_of(SIM["web"])}))


def adopt_sim():
    """Take back a simulator a previous run of this server started."""
    try:
        r = json.loads(SIM_RECORD.read_text())
    except (OSError, ValueError):
        return
    if alive(r["sim_pgid"]) or alive(r["web_pgid"]):
        SIM.update(proc=r["sim_pgid"], web=r["web_pgid"], name=r["name"],
                   preset=r["preset"], started=r["started"])
    else:
        SIM_RECORD.unlink(missing_ok=True)


def sim_status():
    p, web = SIM["proc"], SIM["web"]
    out = {"running": alive(p), "name": SIM["name"], "preset": SIM["preset"],
           "gcs": GCS_URL, "profile": "World maker simulation"}
    if not SIM["name"]:
        out["other_simulator"] = simulator_running()
        return out
    out["elapsed_s"] = time.time() - SIM["started"]
    out["web_host"] = alive(web)
    out["gcs_up"] = out["running"] and alive(web) and port_open(GCS_PORT)
    # The gateway serves once Gazebo and SITL are up; the aggregator only
    # after the operator's Connect starts the production runtime.
    out["gateway_up"] = out["running"] and port_open(8090)
    out["runtime_up"] = out["running"] and port_open(8765)
    out["log_tail"] = tail(LOGS / f"{SIM['name']}_manual.log", 8)
    if not out["running"] and p is not None and not isinstance(p, int):
        out["exit_code"] = p.returncode
    return out


def install_sim_delivery_profile():
    """The SIMULATOR's loaded/unloaded hover-effort calibration (the one the
    recorded acceptance runs use), installed where the web host looks for a
    profile's delivery calibration. Without one the aircraft refuses to lower
    the payload. It describes the simulated airframe only, never the drone."""
    if not SIM_DELIVERY_PROFILE.is_file():
        return ""
    devices = WEB_STATE / "devices"
    devices.mkdir(parents=True, exist_ok=True)
    (devices / SIM_DELIVERY_NAME).write_bytes(SIM_DELIVERY_PROFILE.read_bytes())
    return SIM_DELIVERY_NAME


def write_profile(spec):
    """The web host's laptop-simulation profile for this world, selected.

    Other saved profiles are kept. Not auto-connecting: Connect in the GCS
    starts the production runtime, as on the Pi.
    """
    WEB_STATE.mkdir(parents=True, exist_ok=True)
    path = WEB_STATE / "profiles.json"
    try:
        profiles = json.loads(path.read_text())
    except (OSError, ValueError):
        profiles = {}
    profiles[PROFILE_ID] = {
        "id": PROFILE_ID, "name": "World maker simulation", "vehicle": "simulation",
        "transport": "tcp", "host": "127.0.0.1", "port": 5762, "bind_port": 14555,
        "system_id": 1, "component_id": 1, "gateway": "http://127.0.0.1:8090",
        "device": "/dev/ttyAMA0", "baud": 115200, "camera_device": "/dev/video0",
        "lidar_port": "/dev/ttyUSB0", "lidar_yaw_deg": 0.0, "lidar_mirrored": False,
        "camera_hfov": 0.851919, "marker_m": float(spec["qr"]["target_m"]),
        "rc_config": {}, "slam": True, "hardware_reviewed": False,
        "delivery_calibration": install_sim_delivery_profile(),
        "gcs_host": "", "winch_backend": "mavlink",
        "venue_file": str(SIM_VENUE) if SIM_VENUE.is_file() else "",
        "autoconnect": False, "slam_odometry": "fcu"}
    for name, data in ((path, profiles), (WEB_STATE / "connection-selection.json",
                                          {"profile_id": PROFILE_ID})):
        tmp = name.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        os.replace(tmp, name)
    tiles = WEB_STATE / "map-tiles"
    if OFFLINE_TILES.is_dir() and not tiles.exists():
        tiles.symlink_to(OFFLINE_TILES)


def start_sim(name):
    f = WORLDS / f"{name}.json"
    if RUN["proc"] and RUN["proc"].poll() is None:
        return 409, {"error": f"the scripted run '{RUN['name']}' is still flying"}
    if alive(SIM["proc"]) or alive(SIM["web"]) or simulator_running():
        return 409, {"error": "a simulator is already running; stop it first"}
    if port_open(GCS_PORT) or port_open(8765):
        return 409, {"error": f"port {GCS_PORT} or 8765 is in use: another GCS or "
                              "runtime is running"}
    if not NAME_RE.match(name) or not f.exists():
        return 404, {"error": "save the world first"}
    spec = json.loads(f.read_text())
    errs, _ = validate(spec)
    if errs:
        return 400, {"error": "the world has errors: " + "; ".join(errs)}
    if not spec.get("dimensions"):
        return 400, {"error": "apply arena dimensions first: they become the GCS preset"}
    preset = save_gcs_preset(preset_name(name), spec["dimensions"])
    write_profile(spec)
    env = dict(os.environ)
    for leak in ("AEROTHON_RANDOM_ARENA", "AEROTHON_SEED", "AEROTHON_DELIVERY_ZONE",
                 "AEROTHON_GEOFENCE", "AEROTHON_CONDITIONS", "AEROTHON_HEADLESS",
                 "ROS_DOMAIN_ID", "ROS_LOCALHOST_ONLY"):
        env.pop(leak, None)
    LOGS.mkdir(parents=True, exist_ok=True)
    log = open(LOGS / f"{name}_manual.log", "w")
    # Laptop half: Gazebo (with its window), SITL and the sensor gateway. The
    # launcher publishes no geofence or banner colours in this mode: the
    # operator enters them in the GCS.
    sim_env = dict(env, **{
        "AEROTHON_WORLD_SPEC": str(f),
        "AEROTHON_TARGET_QR_M": str(spec["qr"]["target_m"]),
        "AEROTHON_START_QR_M": str(spec["qr"]["start_m"]),
        # The master guide's render size for closed-loop runs on this laptop.
        "AEROTHON_CAMERA_W": "960", "AEROTHON_CAMERA_H": "540",
        "AEROTHON_OPEN_GCS": "0",
        "PYTHONPATH": f"{ROOT / 'src/aerothon_runtime'}:{env.get('PYTHONPATH', '')}",
    })
    if GATEWAY_PYTHON.exists():
        sim_env["AEROTHON_GATEWAY_PYTHON"] = str(GATEWAY_PYTHON)
    SIM["proc"] = subprocess.Popen(
        ["bash", str(ROOT / "scripts" / "launch_laptop_sim.sh")], cwd=ROOT, env=sim_env,
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    # The real web host serving the GCS; Connect starts the production runtime.
    web_env = dict(env, ROS_DOMAIN_ID=RUNTIME_DOMAIN, AEROTHON_MAP_ONLINE="0",
                   AEROTHON_DEVICE_STATE_DIR=str(WEB_STATE / "devices"),
                   PYTHONPATH=f"{ROOT / 'src/aerothon_runtime'}:{env.get('PYTHONPATH', '')}")
    (WEB_STATE / "devices").mkdir(parents=True, exist_ok=True)
    SIM["web"] = subprocess.Popen(
        ["bash", "-c", ROS_ENV + 'exec /usr/bin/python3 -m aerothon_runtime.web --static "$1" '
         '--state-dir "$2" --bind 127.0.0.1 --port "$3"', "_",
         str(ROOT / "src/aerothon_gcs/tauri_app/dist"), str(WEB_STATE), str(GCS_PORT)],
        cwd=ROOT, env=web_env, stdout=open(LOGS / f"{name}_webhost.log", "w"),
        stderr=subprocess.STDOUT, start_new_session=True)
    SIM.update(name=name, preset=preset, started=time.time())
    remember_sim()
    return 200, {"started": name, "preset": preset}


def stop_group(handle, waits=((signal.SIGINT, 15), (signal.SIGTERM, 10), (signal.SIGKILL, 5))):
    """Stop the process group ``handle`` leads, and its stragglers."""
    if not alive(handle):
        return
    pgid = pgid_of(handle)
    for sig, wait in waits:
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return
        end = time.time() + wait
        while time.time() < end and alive(handle):
            time.sleep(0.5)
        if not alive(handle):
            return
    # gz server and arducopter outlive the launcher in the same group.
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.5)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def stop_sim(force=False):
    if not (alive(SIM["proc"]) or alive(SIM["web"])):
        return 409, {"error": "no simulator started from here is running"}
    armed = aircraft_armed() if port_open(8765) else False
    if armed:
        return 409, {"error": "the aircraft is armed: land and disarm it from the GCS first"}
    if armed is None and not force:
        return 409, {"error": "cannot read the armed state from the GCS; "
                              "confirm the aircraft is disarmed to stop anyway",
                     "confirm": True}
    # The production runtime is the web host's own process group: Disconnect
    # stops it behind the web host's disarm gate before anything else goes.
    if alive(SIM["web"]) and port_open(8765):
        req = urllib.request.Request(f"http://127.0.0.1:{GCS_PORT}/api/disconnect",
                                     method="POST", data=b"{}",
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=60).read()
        except OSError as error:
            if not force:
                return 409, {"error": f"the GCS did not disconnect the runtime ({error}); "
                                      "disconnect it in Connections, or confirm to stop anyway",
                             "confirm": True}
    stop_group(SIM["web"])
    stop_group(SIM["proc"])
    SIM_RECORD.unlink(missing_ok=True)
    return 200, {"stopped": SIM["name"]}


def organiser(name=None):
    """The organiser inputs for world ``name``; without one, the FCU home."""
    f = WORLDS / f"{name}.json" if name else None
    if name and (not NAME_RE.match(name) or not f.exists()):
        return 404, {"error": "no such world"}
    args = ["--home-only"] if f is None else [str(f)]
    # MAVROS runs in the production runtime: its domain, localhost-only.
    env = dict(os.environ, ROS_DOMAIN_ID=RUNTIME_DOMAIN, ROS_LOCALHOST_ONLY="1",
               ROS_AUTOMATIC_DISCOVERY_RANGE="LOCALHOST")
    try:
        res = subprocess.run(
            ["bash", "-c", ROS_ENV + 'exec python3 scripts/organiser_inputs.py "$@"', "_", *args],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=40)
    except subprocess.TimeoutExpired:
        return 504, {"error": "timed out waiting for the FCU home position"}
    try:
        out = json.loads(res.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return 500, {"error": (res.stderr or res.stdout).strip()[-400:] or "no output"}
    if "error" in out:
        out["error"] = "no FCU home yet: Connect in the GCS first (the runtime's MAVROS supplies it)"
        return 503, out
    if name:
        out["preset"] = preset_name(name)
    return 200, out


def validate(spec):
    """world_spec's verdict, from the file as it is NOW.

    Imported once, a rule added to world_spec.py while the server ran never
    reached it: the server passed a world that run_custom_world.sh (a fresh
    import) then refused, and the editor sat on "starting the simulator".
    """
    importlib.reload(world_spec)
    return world_spec.validate(spec)


def tail(path, n=8):
    try:
        return path.read_text(errors="replace").splitlines()[-n:]
    except OSError:
        return []


def last_line(path, needle):
    try:
        lines = [l for l in path.read_text(errors="replace").splitlines() if needle in l]
    except OSError:
        return ""
    return lines[-1] if lines else ""


def run_status():
    p, name = RUN["proc"], RUN["name"]
    out = {"running": bool(p and p.poll() is None), "name": name}
    if not name:
        return out
    out["elapsed_s"] = time.time() - RUN["started"] if out["running"] else None
    # The live log is shared with every run; until this run's stack rewrites
    # it, it still holds the LAST run's result.
    try:
        fresh = LIVE_LOG.stat().st_mtime >= RUN["started"]
    except OSError:
        fresh = False
    if not fresh:
        if out["running"]:
            out["state"], out["result"] = "starting the simulator", ""
            out["log_tail"] = tail(LOGS / f"{name}.out", 6)
        else:
            # Ended before the stack ever wrote the live log: the runner
            # refused or crashed, and its own log says why.
            out["state"] = ""
            out["result"] = (f"FAILED TO START (runner exit code "
                             f"{RUN['proc'].returncode})")
            out["log_tail"] = (tail(LOGS / f"{name}.runner.log")
                               or tail(LOGS / f"{name}.out"))
        return out
    state = last_line(LIVE_LOG, "Mission state ->")
    out["state"] = state.split("Mission state ->")[-1].strip() if state else ""
    result = last_line(LIVE_LOG, "Mission result:")
    out["result"] = result.split("Mission result:")[-1].strip() if result else ""
    grade = LOGS / f"{name}_grade.txt"
    if grade.exists() and not out["running"]:
        out["grade"] = [l.strip() for l in grade.read_text().splitlines()
                        if l.strip().startswith("[")]
    video = LOGS / f"{name}.mp4"
    if video.exists() and not out["running"]:
        out["video"] = str(video.relative_to(ROOT))
    run_out = LOGS / f"{name}.out"
    if run_out.exists():
        out["log_tail"] = run_out.read_text(errors="replace").splitlines()[-6:]
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            body = (HERE / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/worlds":
            WORLDS.mkdir(parents=True, exist_ok=True)
            self._json(200, {"worlds": sorted(p.stem for p in WORLDS.glob("*.json"))})
        elif path.startswith("/api/worlds/"):
            name = unquote(path.rsplit("/", 1)[1])
            f = WORLDS / f"{name}.json"
            if not NAME_RE.match(name) or not f.exists():
                self._json(404, {"error": "no such world"})
            else:
                self._json(200, json.loads(f.read_text()))
        elif path == "/api/run":
            self._json(200, run_status())
        elif path == "/api/dimensions":
            self._json(200, dimension_catalogue())
        elif path == "/api/sim":
            self._json(200, sim_status())
        elif path == "/api/home":
            self._json(*organiser())
        elif path.startswith("/api/organiser/"):
            self._json(*organiser(unquote(path.rsplit("/", 1)[1])))
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        url = urlparse(self.path)
        path = url.path
        if path == "/api/validate":
            errs, warns = validate(self._body())
            self._json(200, {"errors": errs, "warnings": warns})
        elif path == "/api/apply_dimensions":
            body = self._body()
            try:
                importlib.reload(world_spec)
                spec = world_spec.apply_dimensions(body.get("spec") or {},
                                                   body.get("dimensions") or {})
            except (ValueError, TypeError) as error:
                self._json(400, {"error": str(error)})
                return
            self._json(200, {"spec": spec})
        elif path.startswith("/api/sim/start/"):
            self._json(*start_sim(unquote(path.rsplit("/", 1)[1])))
        elif path == "/api/sim/stop":
            self._json(*stop_sim(parse_qs(url.query).get("force", ["0"])[0] == "1"))
        elif path.startswith("/api/worlds/"):
            name = unquote(path.rsplit("/", 1)[1])
            if not NAME_RE.match(name):
                self._json(400, {"error": "names are letters, digits, _ and - only"})
                return
            spec = self._body()
            spec["name"] = name
            spec["schema"] = world_spec.SCHEMA
            WORLDS.mkdir(parents=True, exist_ok=True)
            f = WORLDS / f"{name}.json"
            f.write_text(json.dumps(spec, indent=2) + "\n")
            errs, warns = validate(spec)
            reply = {"path": str(f.relative_to(ROOT)), "errors": errs, "warnings": warns}
            # The world's dimensions become the GCS preset the operator applies.
            if spec.get("dimensions"):
                try:
                    reply["preset"] = save_gcs_preset(preset_name(name), spec["dimensions"])
                except (ValueError, OSError) as error:
                    reply["preset_error"] = str(error)
            self._json(200, reply)
        elif path.startswith("/api/run/"):
            name = unquote(path.rsplit("/", 1)[1])
            f = WORLDS / f"{name}.json"
            if RUN["proc"] and RUN["proc"].poll() is None:
                self._json(409, {"error": f"'{RUN['name']}' is still flying"})
                return
            if alive(SIM["proc"]):
                self._json(409, {"error": "the manual simulator is running; stop it first"})
                return
            if not NAME_RE.match(name) or not f.exists():
                self._json(404, {"error": "save the world first"})
                return
            errs, _ = validate(json.loads(f.read_text()))
            if errs:
                self._json(400, {"error": "the world has errors: " + "; ".join(errs)})
                return
            q = parse_qs(url.query)
            args = ["bash", str(ROOT / "scripts" / "run_custom_world.sh"), str(f)]
            if q.get("gui", ["0"])[0] == "1":
                args.append("--gui")
            if q.get("record", ["0"])[0] == "1":
                args.append("--record")
            LOGS.mkdir(parents=True, exist_ok=True)
            RUN["proc"] = subprocess.Popen(
                args, cwd=ROOT, stdout=open(LOGS / f"{name}.runner.log", "w"),
                stderr=subprocess.STDOUT, start_new_session=True)
            RUN["name"], RUN["started"] = name, time.time()
            self._json(200, {"started": name})
        else:
            self._json(404, {"error": "not found"})


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8777)
    args = ap.parse_args()
    adopt_sim()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"world editor on http://127.0.0.1:{args.port}/  (worlds in {WORLDS})")
    srv.serve_forever()


if __name__ == "__main__":
    main()
