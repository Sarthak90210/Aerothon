import { lazy, Suspense, useEffect, useLayoutEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Telemetry } from "./types";
import { TelemetryHistory } from "./telemetryHistory";
import {
  acknowledgement,
  commandId,
  age,
  freshFcu,
  missionActive,
  startAllowed,
  startBlockReason,
  executionActive,
  reviewAllowed,
  taskCommand,
  tasks,
  videoUrl,
  type CommandOutcome,
  api,
  ApiError,
  type HostState,
  vehicleLabel,
} from "./runtime";
import Connections from "./Connections";
import ArenaDimensions from "./ArenaDimensions";
import LidarCalibration from "./LidarCalibration";
import CameraCalibration from "./CameraCalibration";
import WinchCalibration from "./WinchCalibration";
import Slam, { type Grid, type MapPose } from "./LidarView";
import { decodeGrid } from "./lidarGeometry";
import coverage from "./satelliteCoverage.json";
import { satelliteStyle } from "./mapSources";
import { organiserFence } from "./organiser";
import OrganiserPoints from "./OrganiserPoints";
import "./gcs.css";
const Graphs = lazy(() => import("./Graphs"));

// Shown wherever a value is missing or stale.
const NA = "—";
// toFixed keeps the sign of a value that rounds to zero ("-0.0 m" on the pad).
const value = (n: unknown, unit = "", precision = 1) =>
  typeof n === "number" && Number.isFinite(n)
    ? `${n.toFixed(precision).replace(/^-(0(\.0+)?)$/, "$1")}${unit}`
    : NA;
// Readiness values are numbers, text or, for detectors, {name: age seconds}.
const readinessValue = (v: unknown): string =>
  v && typeof v === "object"
    ? Object.entries(v as Record<string, unknown>)
        .map(([name, age]) => `${name} ${value(age, " s")}`)
        .join(", ")
    : String(v ?? NA);
// The fence as GeoJSON for the map: [lat, lon] pairs, closed ring.
const EMPTY = { type: "FeatureCollection", features: [] } as const;
const fenceGeo = (pts: [number, number][]) =>
  pts.length < 3
    ? EMPTY
    : {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            properties: {},
            geometry: {
              type: "Polygon",
              coordinates: [
                [...pts, pts[0]].map(([lat, lon]) => [lon, lat]),
              ],
            },
          },
        ],
      };
// Banner roles (perception_banner/colours.py): green marks the entry
// corridor, exit the exit corridor the return lap takes (blue on the field
// PDF), orange the rulebook's no-entry boards. Green and red are required,
// and one of exit or orange.
type Colours = { green: string; exit: string; orange: string; red: string };
const COLOUR_LABELS: Record<keyof Colours, string> = {
  green: "Entry corridor banner (green)",
  exit: "Exit corridor banner (return lap)",
  orange: "No-entry banner (orange, if any)",
  red: "Red zone",
};
const HEX = /^#[0-9a-fA-F]{6}$/;
const suppliedColours = (c: Colours) =>
  Object.fromEntries(Object.entries(c).filter(([, v]) => v.trim() !== ""));
const coloursReady = (c: Colours) =>
  HEX.test(c.green) &&
  HEX.test(c.red) &&
  (HEX.test(c.exit) || HEX.test(c.orange)) &&
  Object.values(suppliedColours(c)).every((v) => HEX.test(v));
const boundary = (text: string) =>
  text
    .trim()
    .split("\n")
    .filter(Boolean)
    .map((line) => {
      const [lat, lon, ...extra] = line.split(",").map(Number);
      if (extra.length || !Number.isFinite(lat) || !Number.isFinite(lon))
        throw new Error("Enter latitude, longitude on each line");
      return { lat, lon };
    });
export default function App() {
  const [mode, setMode] = useState<"flight" | "testing">("flight"),
    [theme, setTheme] = useState(localStorage.getItem("gcs-theme") || "light");
  const [view, setView] = useState<"camera" | "slam" | "map" | "graphs">("map");
  const activeEndpoint = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`;
  const [hostState, setHostState] = useState<HostState | null>(null);
  const [waypoints, setWaypoints] = useState('');
  async function refreshHost() {
    try { setHostState(await api('/api/state')); } catch { setHostState(null); }
  }
  useEffect(() => { void refreshHost(); const timer = window.setInterval(() => void refreshHost(), 2000); return () => window.clearInterval(timer); }, []);
  const [linked, setLinked] = useState(false),
    [received, setReceived] = useState(0),
    [clock, setClock] = useState(Date.now()),
    [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [events, setEvents] = useState<string[]>([]),
    [error, setError] = useState("");
  const [settings, setSettings] = useState(false),
    [arenaOpen, setArenaOpen] = useState(false),
    [lidarOpen, setLidarOpen] = useState(false),
    [cameraCalOpen, setCameraCalOpen] = useState(false),
    [winchCalOpen, setWinchCalOpen] = useState(false);
  const [task, setTask] = useState("mission"),
    [action, setAction] = useState("stow"),
    [height, setHeight] = useState(5);
  const [review, setReview] = useState<{
      cmd: string;
      args: Record<string, unknown>;
      label: string;
    } | null>(null),
    [busy, setBusy] = useState(false),
    [starting, setStarting] = useState(false);
  const [outcome, setOutcomeState] = useState<CommandOutcome | null>(null),
    [outcomeAt, setOutcomeAt] = useState(0);
  const setOutcome = (next: CommandOutcome) => {
    setOutcomeState(next);
    setOutcomeAt(Date.now());
  };
  const [target, setTarget] = useState(""),
    [mapReady, setMapReady] = useState(false);
  const [colours, setColours] = useState({
    green: "",
    exit: "",
    orange: "",
    red: "",
  });
  const [topic, setTopic] = useState("/percep/overlay");
  const [grid, setGrid] = useState<Grid | null>(null),
    [gridReceived, setGridReceived] = useState(0),
    [onlineMap, setOnlineMap] = useState(false),
    [mapError, setMapError] = useState(false);
  const history = useRef(new TelemetryHistory()),
    socket = useRef<WebSocket | null>(null),
    mapHost = useRef<HTMLDivElement>(null),
    map = useRef<maplibregl.Map | null>(null),
    marker = useRef<maplibregl.Marker | null>(null),
    centered = useRef(false);
  // The command this browser sent last: only its own results replace the
  // outcome line. The runtime republishes the previous run's terminal status
  // every 0.2 s, which used to erase a refusal reason within a moment.
  const latestCommand = useRef(""),
    sentCommands = useRef(new Map<string, string>()),
    lastExecution = useRef(""),
    trail = useRef<Array<[number, number]>>([]),
    trailFrame = useRef<string | null>(null),
    mapSession = useRef<string | null>(null);
  const pending = useRef(
    new Map<
      string,
      { timer: number; resolve: (result: CommandOutcome) => void; cmd: string }
    >(),
  );
  const fresh = linked && received > 0 && clock - received < 3000,
    t = fresh ? telemetry : null,
    fcu = freshFcu(t),
    running = missionActive(t) || starting;
  // Manual flight mode: no detectors run, so the raw camera is the only feed.
  const manualMode = telemetry?.runtime_mode === "manual" || hostState?.mode === "manual",
    feed = manualMode ? "/image_raw" : topic;
  const selectedTask = mode === "flight" ? "mission" : task,
    taskInfo = tasks.find((item) => item.id === selectedTask)!;
  const canStart = !busy && !starting && startAllowed(t, fresh, selectedTask);
  const record = (text: string) =>
    setEvents((list) => [
      ...list.slice(-149),
      `${new Date().toLocaleTimeString()} ${text}`,
    ]);
  // A different vehicle or a restarted runtime is a new SLAM session: the
  // previous map must not stay on screen looking current.
  const session = hostState ? `${hostState.profile_id}|${hostState.runtime}` : null;
  useEffect(() => {
    if (session === null) return;
    if (mapSession.current !== null && mapSession.current !== session) {
      setGrid(null);
      setGridReceived(0);
      trail.current = [];
    }
    mapSession.current = session;
  }, [session]);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("gcs-theme", theme);
  }, [theme]);
  useEffect(() => {
    const timer = window.setInterval(() => {
      setClock(Date.now());
      history.current.tick(performance.now(), Date.now());
    }, 500);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    let disposed = false,
      retry = 0;
    const open = () => {
      let opened = false;
      const streamUrl = new URL(activeEndpoint);
      streamUrl.searchParams.set('map_encoding', 'rle');
      const ws = new WebSocket(streamUrl);
      socket.current = ws;
      ws.onopen = () => {
        if (disposed || socket.current !== ws) return;
        opened = true;
        setLinked(true);
        record(`Connected to ${activeEndpoint}`);
      };
      ws.onmessage = (event) => {
        if (disposed || socket.current !== ws) return;
        try {
          const envelope = JSON.parse(event.data);
          if (envelope.kind === "telemetry") {
            history.current.ingest(
              envelope.data,
              envelope.t,
              performance.now(),
              Date.now(),
            );
            setTelemetry(envelope.data);
            setReceived(Date.now());
            const pose = envelope.data.slam_pose;
            if (pose && Number.isFinite(pose.x) && Number.isFinite(pose.y)) {
              const poseFrame = typeof pose.frame === 'string' ? pose.frame : '';
              if (trailFrame.current !== poseFrame) trail.current = [];
              trailFrame.current = poseFrame;
              const last = trail.current[trail.current.length - 1];
              if (!last || Math.hypot(pose.x - last[0], pose.y - last[1]) > 0.05)
                trail.current = [...trail.current.slice(-599), [pose.x, pose.y]];
            }
            if (
              age(envelope.data, "mission") < 3 &&
              envelope.data.mission?.state !== "STARTING"
            )
              setStarting(false);
          } else if (envelope.kind === "execution" || envelope.kind === "receipt") {
            const d = envelope.data,
              name = envelope.kind === "execution"
                ? tasks.find((x) => x.id === d.task)?.label ?? "Execution"
                : sentCommands.current.get(d.command_id) ?? "Runtime";
            if (envelope.kind === "receipt")
              record(`${name}: ${d.state}${d.reason ? `, ${d.reason}` : ""}`);
            else {
              const key = `${d.command_id}|${d.state}|${d.stage ?? ""}|${d.reason ?? ""}`;
              if (lastExecution.current && key !== lastExecution.current)
                record(`${name}: ${d.state}${d.stage ? ` · ${d.stage}` : ""}${d.reason ? `, ${d.reason}` : ""}`);
              lastExecution.current = key;
            }
            if (d.command_id && d.command_id === latestCommand.current)
              setOutcome({ ...d, cmd: name });
            setStarting(false);
          } else if (envelope.kind === "map") {
            const next = decodeGrid(envelope.data);
            // A restarted slam_toolbox starts a new map and a new track.
            setGrid((old) => {
              if (old && (next.stamp < old.stamp - 1 || next.frame !== old.frame)) trail.current = [];
              return next;
            });
            setGridReceived(Date.now());
          } else if (envelope.kind === "event")
            record(envelope.data.msg || "Runtime event");
          else if (envelope.kind === "ack") {
            const result = acknowledgement(envelope.data),
              entry = pending.current.get(result.command_id);
            if (entry) {
              window.clearTimeout(entry.timer);
              pending.current.delete(result.command_id);
              entry.resolve(result);
            }
            if (result.command_id === latestCommand.current) setOutcome(result);
            record(
              `${result.cmd}: ${result.state}${result.reason ? `, ${result.reason}` : ""}`,
            );
          }
        } catch {
          setError("The runtime sent an invalid message.");
        }
      };
      ws.onclose = (event) => {
        if (disposed || socket.current !== ws) return;
        if (opened)
          record(`Link to the Pi lost (code ${event.code}${event.reason ? `: ${event.reason}` : ""}); reconnecting`);
        setLinked(false);
        history.current.disconnect();
        for (const [id, entry] of pending.current) {
          window.clearTimeout(entry.timer);
          const result: CommandOutcome = {
            command_id: id,
            cmd: entry.cmd,
            state: "Outcome unknown",
            reason: "Connection lost; this command will not be replayed.",
          };
          entry.resolve(result);
          setOutcome(result);
        }
        pending.current.clear();
        if (!disposed) retry = window.setTimeout(open, 1500);
      };
    };
    open();
    return () => {
      disposed = true;
      window.clearTimeout(retry);
      socket.current?.close();
      for (const [id, entry] of pending.current) {
        window.clearTimeout(entry.timer);
        entry.resolve({
          command_id: id,
          cmd: entry.cmd,
          state: "Outcome unknown",
          reason: "Connection changed; no retry was sent.",
        });
      }
      pending.current.clear();
    };
  }, [activeEndpoint]);
  async function send(
    cmd: string,
    args: Record<string, unknown> = {},
  ): Promise<CommandOutcome> {
    const ws = socket.current;
    if (!ws || ws.readyState !== WebSocket.OPEN)
      throw new Error("Production runtime is disconnected.");
    const id = commandId();
    latestCommand.current = id;
    sentCommands.current.set(id, cmd);
    const submitted: CommandOutcome = {
        command_id: id,
        cmd,
        state: "Submitted",
        reason: "Waiting for the runtime.",
      };
    setOutcome(submitted);
    record(`${cmd}: Submitted`);
    try {
      const result = await api('/api/commands', {command_id:id, cmd, args, confirm:true});
      setOutcome({...result, cmd});
      return {...result, cmd};
    } catch (e) {
      const result: CommandOutcome = {...submitted, state: e instanceof ApiError ? 'Failed' : 'Outcome unknown', reason: e instanceof Error ? e.message : String(e)};
      setOutcome(result);
      return result;
    }
  }

  async function perform(cmd: string, args: Record<string, unknown> = {}) {
    setBusy(true);
    setError("");
    try {
      const result = await send(cmd, args);
      if (result.state === "Failed")
        throw new Error(result.reason || "Runtime rejected the request");
      if (cmd === "start") setStarting(true);
      if (cmd === "abort" && result.state === "Accepted") setStarting(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  }
  // A window's reviewed command is confirmed in that window. It used to close
  // the window and wait for Confirm in the Mission panel, where operators
  // missed it: Camera cal "applied" and the calibration never left the GCS
  // (aircraft, 28 Oct 2026).
  const overlayOpen = arenaOpen || lidarOpen || cameraCalOpen || winchCalOpen;
  const reviewedSend = (
    cmd: string,
    args: Record<string, unknown> = {},
    danger = false,
    label?: string,
  ) => {
    if (danger)
      setReview({ cmd, args, label: label ?? `${cmd.replace(/_/g, " ")}${args.mode ? ` ${args.mode}` : ""}` });
    else void perform(cmd, args);
  };
  const closeOverlay = (close: (open: boolean) => void) => () => {
    setReview(null);
    close(false);
  };
  useEffect(() => {
    if (view !== "map" || !mapHost.current) return;
    const satellite = satelliteStyle(coverage, onlineMap, location.origin);
    const m = new maplibregl.Map({
      container: mapHost.current,
      center: coverage.initial.center as [number, number],
      zoom: coverage.initial.zoom,
      maxZoom: 19,
      style: {
        version: 8,
        sources: satellite.sources,
        layers: [
          {
            id: "background",
            type: "background",
            paint: {
              "background-color": theme === "dark" ? "#252627" : "#ecece8",
            },
          },
          ...(satellite.layers as maplibregl.LayerSpecification[]),
        ],
      },
    });
    map.current = m;
    // Diagnostic handle for browser checks of the map's sources and layers.
    (mapHost.current as any).aerothonMap = m;
    marker.current = new maplibregl.Marker({
      color: theme === "dark" ? "#eee" : "#242424",
    });
    centered.current = false;
    setMapError(false);
    m.addControl(new maplibregl.NavigationControl(), "top-right");
    m.on("error", () => setMapError(true));
    setMapReady(false);
    // The judges' geofence: applied (filled) and the typed draft (dashed).
    // Added once the style is parsed ("style.load"): "load" and
    // isStyleLoaded() also wait for every tile, which may never finish.
    const addFence = () => {
      if (m.getSource("fence-applied")) return;
      try {
        m.addSource("fence-applied", { type: "geojson", data: EMPTY as any });
        m.addSource("fence-draft", { type: "geojson", data: EMPTY as any });
        m.addLayer({ id: "fence-applied-fill", type: "fill", source: "fence-applied",
          paint: { "fill-color": "#e8a33d", "fill-opacity": 0.15 } });
        m.addLayer({ id: "fence-applied-line", type: "line", source: "fence-applied",
          paint: { "line-color": "#e8a33d", "line-width": 2.5 } });
        m.addLayer({ id: "fence-draft-line", type: "line", source: "fence-draft",
          paint: { "line-color": "#3d8be8", "line-width": 2, "line-dasharray": [2, 2] } });
        setMapReady(true);
      } catch {
        /* Style not parsed yet; the next style event adds them. */
      }
    };
    // An inline style can finish parsing inside the constructor, before
    // any listener exists, so try now as well as on every style event.
    addFence();
    m.on("style.load", addFence);
    m.on("styledata", addFence);
    m.on("load", addFence);
    return () => {
      marker.current?.remove();
      m.remove();
      map.current = null;
    };
  }, [view, onlineMap, theme]);
  // Draw the fence: the applied polygon and the outline of the organiser
  // points stored so far (dashed), as Apply will send it.
  const stored = t?.organiser_points?.points ?? {};
  const pick = (keys: string[]) => keys.filter((k) => stored[k]).map((k) => stored[k]);
  const zonePts = pick(["zone_1", "zone_2", "zone_3", "zone_4"]);
  const outline = organiserFence(pick(["fence_back_left", "fence_back_right"]),
                                 zonePts.length === 4 ? zonePts : []);
  const draftFence: [number, number][] = outline.length >= 3
    ? outline.map((p) => [p.lat, p.lon] as [number, number]) : [];
  const draftKey = JSON.stringify(draftFence);
  const appliedFence = t?.geofence_vertices ?? [];
  const appliedKey = JSON.stringify(appliedFence);
  useEffect(() => {
    const m = map.current;
    if (!m || !mapReady) return;
    (m.getSource("fence-applied") as maplibregl.GeoJSONSource | undefined)
      ?.setData(fenceGeo(appliedFence) as any);
    (m.getSource("fence-draft") as maplibregl.GeoJSONSource | undefined)
      ?.setData(fenceGeo(draftFence) as any);
    if (mapHost.current) {
      mapHost.current.dataset.fenceDraft = String(draftFence.length);
      mapHost.current.dataset.fenceApplied = String(appliedFence.length);
    }
    const show = draftFence.length >= 3 ? draftFence : appliedFence;
    if (show.length >= 3) {
      const lons = show.map((p) => p[1]), lats = show.map((p) => p[0]);
      m.fitBounds([[Math.min(...lons), Math.min(...lats)],
                   [Math.max(...lons), Math.max(...lats)]],
                  { padding: 40, maxZoom: 19, duration: 0 });
      centered.current = true;
    }
  }, [mapReady, draftKey, appliedKey]);
  useEffect(() => {
    const gps = t?.gps;
    if (
      view !== "map" ||
      !map.current ||
      !gps ||
      age(t, "gps") >= 3 ||
      gps.fix === "NO" ||
      !Number.isFinite(gps.lat) ||
      !Number.isFinite(gps.lon)
    ) {
      marker.current?.remove();
      return;
    }
    const ll: [number, number] = [gps.lon, gps.lat];
    marker.current?.setLngLat(ll).addTo(map.current);
    if (!centered.current) {
      map.current.jumpTo({ center: ll, zoom: 17 });
      centered.current = true;
    }
  }, [t, view]);
  const reviewBox = review && (
    <section className="review">
      <h3>{review.label}</h3>
      <p>
        {hostState?.profile_id ?? "No vehicle"} · {fcu ? t?.mission.mode : NA} ·{" "}
        {fcu ? (t?.mission.armed ? "Armed" : "Disarmed") : NA}
      </p>
      {["stop", "abort"].includes(review.cmd) && !executionActive(t) && (
        // Stop and Abort act on a production execution. After a manual
        // takeoff from Aircraft controls they were accepted and the
        // aircraft kept hovering.
        <p className="review-warning" role="alert">
          No task running: this will not move the aircraft.
          {t?.mission.armed ? " Armed: use Land or RTL." : ""}
        </p>
      )}
      {review.cmd === "stop" && <p className="task-note">Stage-aware LAND/RTL.</p>}
      <button
        disabled={
          busy || !reviewAllowed(t, linked, review.cmd, review.args)
        }
        onClick={() => {
          const request = review;
          setReview(null);
          void perform(request.cmd, request.args);
        }}
      >
        Confirm
      </button>
      <button onClick={() => setReview(null)}>Cancel</button>
    </section>
  );
  return (
    <div className="app">
      <header>
        <div className="wordmark">
          AeroTHON <span>GCS</span>
        </div>
        <nav aria-label="Operating mode">
          <button
            aria-pressed={mode === "flight"}
            onClick={() => {
              setMode("flight");
              setReview(null);
            }}
          >
            Flight
          </button>
          <button
            aria-pressed={mode === "testing"}
            onClick={() => {
              setMode("testing");
              setReview(null);
            }}
          >
            Testing
          </button>
        </nav>
        <div className="header-end">
          <span className="vehicle-kind">
            {(() => {
              const active = hostState?.profiles.find((x) => x.id === hostState?.profile_id);
              return active ? `${active.name} · ${vehicleLabel(active)}` : vehicleLabel(null);
            })()}
          </span>
          <button onClick={() => setArenaOpen(true)}>Arena</button>
          <button onClick={() => setLidarOpen(true)}>Lidar cal</button>
          <button onClick={() => setCameraCalOpen(true)}>Camera cal</button>
          <button onClick={() => setWinchCalOpen(true)}>Winch cal</button>
          <button onClick={() => setSettings(!settings)}>Connections</button>
          <button
            aria-label="Switch theme"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </header>
      <section className="status-strip" aria-label="Aircraft status">
        <Datum
          label="Connection"
          text={
            fcu
              ? "Live"
              : fresh
                ? "No FCU"
                : linked
                  ? "Waiting"
                  : "Disconnected"
          }
        />
        <Datum label="Mode" text={fcu ? t?.mission.mode || NA : NA} />
        <Datum
          label="Control"
          text={
            fcu
              ? running
                ? t?.execution?.control_owner || "Runtime"
                : "Transmitter / FCU"
              : NA
          }
        />
        <Datum
          label="Armed"
          text={
            fcu && typeof t?.mission.armed === "boolean"
              ? t.mission.armed
                ? "Yes"
                : "No"
              : NA
          }
        />
        <Datum
          label="Battery"
          text={value(age(t, "power") < 3 ? t?.power.pct : null, "%", 0)}
        />
        <Datum
          label="Sats"
          text={value(age(t, "sats") < 3 ? t?.gps.sats : null, "", 0)}
        />
        <Datum
          label="Height"
          text={value(age(t, "pose") < 3 ? t?.flight.alt : null, " m")}
        />
        <Datum label="Task" text={!t?.execution ? t?.mission.state || NA : (() => {
          const label = tasks.find((x) => x.id === t.execution?.task)?.label ?? t.execution.task;
          // A finished run is history: "qr: Failed" during a manual flight read as current.
          return executionActive(t)
            ? `${label}: ${t.execution.state}${t.execution.stage ? ` · ${t.execution.stage}` : ""}`
            : `Idle · last ${label} ${t.execution.state.toLowerCase()}`;
        })()} />
      </section>
      <div className="toasts">
        {error && (
          <div className="toast" role="alert">
            <p>{error}</p>
            <button aria-label="Dismiss" onClick={() => setError("")}>×</button>
          </div>
        )}
        {overlayOpen && outcome && clock - outcomeAt < 8000 && (
          <div className={`toast ${outcome.state === "Failed" ? "" : "info"}`} role="status">
            <p>{outcome.cmd.replace(/_/g, " ")}: {outcome.state}. {outcome.reason}</p>
          </div>
        )}
      </div>
      {settings && <Connections state={hostState} refresh={refreshHost} />}
      <main>
        <section className="workspace">
          <div
            className="view-tabs"
            role="tablist"
            aria-label="Monitoring view"
          >
            {(["camera", "slam", "map", "graphs"] as const).map((tab) => (
              <button
                role="tab"
                key={tab}
                id={`tab-${tab}`}
                aria-selected={view === tab}
                aria-controls={`view-${tab}`}
                onClick={() => setView(tab)}
              >
                {
                  {
                    camera: "Camera",
                    slam: "SLAM",
                    map: "Map",
                    graphs: "Graphs",
                  }[tab]
                }
              </button>
            ))}
          </div>
          <div
            role="tabpanel"
            id={`view-${view}`}
            aria-labelledby={`tab-${view}`}
          >
            {view === "map" && (
              <>
                <div ref={mapHost} className="map-host" />
                <label className="check">
                  <input
                    type="checkbox"
                    checked={onlineMap}
                    onChange={(e) => setOnlineMap(e.target.checked)}
                  />
                  Online imagery
                </label>
                <p className="view-note">
                  {age(t, "gps") < 3
                    ? `${value(t?.gps.lat, "°", 7)}, ${value(t?.gps.lon, "°", 7)}`
                    : "No aircraft position"}
                  {mapError && " · No imagery here: change zoom or use online imagery"}
                </p>
              </>
            )}
            {view === "camera" && (
              <>
                <div className="camera-tools">
                  <label>
                    Feed
                    {/* Manual mode runs no detectors: only the raw camera exists. */}
                    <select
                      value={feed}
                      disabled={manualMode}
                      onChange={(e) => setTopic(e.target.value)}
                    >
                      {!manualMode && <option value="/percep/overlay">Composite</option>}
                      <option value="/image_raw">Raw camera</option>
                      {!manualMode && <>
                        <option value="/percep/qr/annotated">QR</option>
                        <option value="/percep/banner/annotated">Banner</option>
                        <option value="/percep/redzone/annotated">
                          Red zone
                        </option>
                      </>}
                    </select>
                  </label>
                </div>
                <CameraFeed
                  url={videoUrl(activeEndpoint, feed)}
                  topic={feed}
                  live={fresh}
                  device={t?.devices?.camera}
                />
                <p className="view-note">
                  Switching feeds does not move the camera.
                </p>
              </>
            )}
            {view === "slam" && (
              <Slam
                status={telemetry?.slam_status}
                statusAge={age(telemetry, "slam_status")}
                mount={telemetry?.lidar_cal?.applied}
                grid={grid}
                mapAge={gridReceived > 0 ? Math.max(0, clock - gridReceived) / 1000 : null}
                pose={fresh && telemetry?.slam_pose ? (telemetry.slam_pose as MapPose) : null}
                poseAge={age(telemetry, "slam_pose")}
                trail={trail.current}
                theme={theme}
                scan={telemetry?.scan}
                lidarFresh={fresh && age(telemetry, "lidar") < 2}
                slamEnabled={
                  hostState?.runtime === "Running" &&
                  hostState.profiles.find((x) => x.id === hostState.profile_id)?.slam === true
                }
              />
            )}
            {view === "graphs" && (
              <Suspense fallback={<p>Loading graphs…</p>}>
                <Graphs history={history.current} theme={theme} live={fresh} />
              </Suspense>
            )}
          </div>
          <details>
            <summary>Flight details</summary>
            <div className="details-grid">
              <Datum
                label="Roll / pitch"
                text={
                  age(t, "pose") < 3
                    ? `${value(t?.flight.roll_deg, "°")} / ${value(t?.flight.pitch_deg, "°")}`
                    : NA
                }
              />
              <Datum
                label="Heading"
                text={value(age(t, "pose") < 3 ? t?.flight.yaw_deg : null, "°")}
              />
              <Datum
                label="Ground speed"
                text={value(
                  age(t, "velocity") < 3 ? t?.flight.gs : null,
                  " m/s",
                )}
              />
              <Datum
                label="Front range (not clearance)"
                text={value(age(t, "lidar") < 3 ? t?.nav.front_m : null, " m")}
              />
              <Datum
                label="Gap bearing"
                text={value(
                  age(t, "avoidance") < 3 && age(t, "lidar") < 3
                    ? ((t?.nav.centering_err ?? NaN) * 180) / Math.PI
                    : null,
                  "°",
                )}
              />
              <Datum
                label="EKF"
                text={
                  age(t, "ekf") < 3
                    ? String(t?.safety.ekf ?? NA)
                    : NA
                }
              />
              <Datum
                label="FC fence"
                text={
                  age(t, "fence") < 3
                    ? t?.safety.geofence || NA
                    : NA
                }
              />
              <Datum
                label="Delivery error"
                text={value(t?.mission.delivery_offset_m, " m")}
              />
              <Datum
                label="Landing"
                text={t?.mission.landing_precision || NA}
              />
              <Datum
                label="Result"
                text={
                  t?.mission.result
                    ? `${t.mission.result}: ${t.mission.result_reason || ""}`
                    : NA
                }
              />
            </div>
            {t?.checklist && (
              <p className="view-note">
                {Object.entries(t.checklist)
                  .map(([step, done]) => `${step} ${done ? "✓" : "–"}`)
                  .join(" · ")}
              </p>
            )}
          </details>
          <section className="observations">
            <h2>Detections</h2>
            <div className="details-grid">
              <Datum label="Start QR" text={t?.percep.start_qr || NA} />
              <Datum
                label="Target"
                text={
                  t?.percep.mission_target === "<start marker appearance>"
                    ? "Start pattern"
                    : t?.percep.mission_target || "Not set"
                }
              />
              <Datum label="Pattern" text={t?.percep.qr_reference ? "Captured" : NA} />
              <Datum
                label="Pad"
                text={
                  t?.percep.target_match
                    ? `Matched (${(t.percep.qr_match_basis ?? []).join(", ") || "payload"})`
                    : "Unconfirmed"
                }
              />
              <Datum label="Banner" text={t?.percep.banner ? "Detected" : "Unconfirmed"} />
              <Datum label="Red zone" text={t?.percep.redzone_status || "UNKNOWN"} />
              <Datum
                label="Square on"
                text={
                  t?.percep.square_angle_deg == null
                    ? t?.percep.square_reason || NA
                    : `${value(t.percep.square_angle_deg, "°")} at ${value(t.percep.square_standoff_m, " m")}`
                }
              />
              <Datum label="Red exclusions" text={String(t?.percep.redzone_exclusions?.length || 0)} />
              <Datum
                label="QR / banner / red"
                text={t?.detector_rates
                  ? ["qr", "banner", "red"]
                      .map((kind) => value(t.detector_rates?.[kind]?.hz, ""))
                      .join(" / ") + " Hz"
                  : NA}
              />
            </div>
            {!!t?.scans?.length && <table>
              <thead>
                <tr>
                  <th>Kind</th>
                  <th>Payload</th>
                  <th>Status</th>
                  <th>Reason</th>
                  <th>Count</th>
                </tr>
              </thead>
              <tbody>
                {t?.scans?.map((row) => (
                  <tr key={row.key}>
                    <td>{row.kind}</td>
                    <td>{row.payload || "Undecoded"}</td>
                    <td>{row.matched ? "Matched" : row.status}</td>
                    <td>{row.reason}</td>
                    <td>{row.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>}
          </section>
        </section>
        <aside className="task-area">
          <h2>{mode === "flight" ? "Mission" : "Test task"}</h2>
          {mode === "testing" && (
            <label>
              Task
              <select
                value={task}
                disabled={running}
                onChange={(e) => {
                  setTask(e.target.value);
                  setReview(null);
                }}
              >
                {tasks.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
          )}
          <p className="task-note">{taskInfo.description}</p>
          {selectedTask === "mechanism" && (
            <label>
              Action
              <select
                value={action}
                onChange={(e) => setAction(e.target.value)}
              >
                {["lower", "release", "stow", "stop"].map((name) => (
                  <option key={name}>{name}</option>
                ))}
              </select>
            </label>
          )}
          {taskInfo.movement && selectedTask !== 'mission' && <label>Height above home (m)<input type="number" min={1} max={10} value={height} onChange={e => setHeight(Number(e.target.value))}/></label>}
          {selectedTask.startsWith('delivery_') && <label>QR payload<input value={target} onChange={e => setTarget(e.target.value)} /></label>}
          {['delivery_gps','avoidance_route'].includes(selectedTask) && <label>Waypoints (lat, lon per line)<textarea value={waypoints} onChange={e => setWaypoints(e.target.value)} /></label>}
          <button
            disabled={!canStart}
            onClick={() => {
              try {
                const request = taskCommand(selectedTask, action, {height, target, waypoints: waypoints.trim() ? boundary(waypoints) : []});
                setError("");
                setReview({ ...request, label: `Start ${taskInfo.label}` });
              } catch (reason) {
                setError(reason instanceof Error ? reason.message : String(reason));
              }
            }}
          >
            Start…
          </button>
          {!canStart && !busy && !starting && (
            <p className="start-blocked">{startBlockReason(t, fresh, selectedTask)}</p>
          )}
          <button
            disabled={!linked || busy}
            onClick={() =>
              setReview({
                cmd: "stop",
                args: {},
                label: "Stop and return",
              })
            }
          >
            Stop and return
          </button>
          {!overlayOpen && reviewBox}
          {outcome && (
            <p role="status">
              {outcome.cmd}: {outcome.state}. {outcome.reason}
            </p>
          )}
          <details open>
            <summary>Readiness</summary>
            {!fresh && <p>No telemetry</p>}
            {t?.safety.ready_reasons?.map((reason) => (
              <p key={reason}>{reason}</p>
            ))}
            {t?.safety.ready_items?.map((item) => (
              <div className="readiness-row" key={item.key}>
                <span>
                  {item.label}: {item.ok ? "Ready" : item.advisory ? "Check" : "Blocked"}
                </span>
                <span>
                  {readinessValue(item.value)}{item.reason ? ` · ${item.reason}` : ""}
                </span>
              </div>
            ))}
            {fresh && !t?.safety.ready && t?.mission.mode !== "GUIDED" && (
              <p>Flight tasks need GUIDED.</p>
            )}
          </details>
          <details>
            <summary>Organiser inputs</summary>
            <Field label="Target QR payload" text={target} change={setTarget} />
            <button
              disabled={!fresh || busy}
              onClick={() => void perform("set_target", { target })}
            >
              Set target
            </button>
            {(["green", "exit", "orange", "red"] as const).map((name) => (
              <Field
                key={name}
                label={COLOUR_LABELS[name]}
                text={colours[name]}
                placeholder={name === "exit" || name === "orange" ? "#RRGGBB or blank" : "#RRGGBB"}
                change={(shade) => setColours({ ...colours, [name]: shade })}
              />
            ))}
            <button
              disabled={!fcu || busy || t?.mission.armed !== false || !coloursReady(colours)}
              onClick={() =>
                reviewedSend("set_banner_colours", { colours: suppliedColours(colours) }, true)
              }
            >
              Apply colours
            </button>
            <p className="view-note">Colours applied: {t?.banner_colours ? Object.entries(t.banner_colours).map(([name,hex]) => `${name} ${hex}`).join(' · ') : 'none'}</p>
            <OrganiserPoints t={t} busy={busy} fcu={fcu}
              perform={(cmd, args) => void perform(cmd, args)} review={reviewedSend} />
            <p className="view-note">
              Fence applied: {appliedFence.length ? `${appliedFence.length} points (filled on Map)` : "none"};
              the stored points' outline is dashed on the Map.
            </p>
          </details>
          <details>
            <summary>Aircraft controls</summary>
            <p className="task-note">Transmitter and FCU failsafes keep priority.</p>
            <div className="actions">
              <button
                disabled={!fcu || busy || running}
                onClick={() =>
                  reviewedSend("set_mode", { mode: "GUIDED" }, true)
                }
              >
                GUIDED
              </button>
              <button
                disabled={
                  !fcu ||
                  !t?.safety.ready ||
                  t?.mission.mode !== "GUIDED" ||
                  busy ||
                  running
                }
                onClick={() => reviewedSend("arm", {}, true)}
              >
                Arm
              </button>
              <button
                disabled={
                  !fcu ||
                  busy ||
                  t?.mission.armed !== true ||
                  t?.safety.on_ground !== true ||
                  age(t, "extended_state") >= 3
                }
                onClick={() => reviewedSend("disarm", {}, true)}
              >
                Disarm
              </button>
              <button
                disabled={!linked || busy}
                onClick={() => reviewedSend("land", {}, true)}
              >
                Land
              </button>
              <button
                disabled={!linked || busy}
                onClick={() => reviewedSend("set_mode", { mode: "RTL" }, true)}
              >
                RTL
              </button>
              <button
                disabled={!linked || busy}
                onClick={() => reviewedSend("abort", {}, true)}
              >
                Abort
              </button>
            </div>
            <label>
              Takeoff height (m)
              <input
                type="number"
                min="1"
                max="10"
                value={height}
                onChange={(e) => setHeight(Number(e.target.value))}
              />
            </label>
            <button
              disabled={
                !fcu ||
                !t?.safety.ready ||
                t?.mission.mode !== "GUIDED" ||
                busy ||
                running
              }
              onClick={() => reviewedSend("takeoff", { alt: height }, true)}
            >
              Takeoff…
            </button>
            <div className="actions">
              <button
                disabled={!fcu || busy}
                onClick={() =>
                  reviewedSend("gimbal_pitch", { degrees: 0 }, true)
                }
              >
                Camera forward
              </button>
              <button
                disabled={!fcu || busy}
                onClick={() =>
                  reviewedSend("gimbal_pitch", { degrees: -90 }, true)
                }
              >
                Camera down
              </button>
            </div>
            <p className="view-note">Winch: Testing → Mechanism.</p>
          </details>
        </aside>
      </main>
      <footer>
        <details open>
          <summary>Events</summary>
          <div className="event-log">
            {events.length
              ? events.map((event, index) => <div key={index}>{event}</div>)
              : "None yet"}
          </div>
        </details>
      </footer>
      {arenaOpen && (
        <ArenaDimensions
          S={t}
          connected={fcu}
          send={reviewedSend}
          onClose={closeOverlay(setArenaOpen)}
        />
      )}
      {lidarOpen && (
        <LidarCalibration
          S={t}
          connected={fcu}
          send={reviewedSend}
          onClose={closeOverlay(setLidarOpen)}
        />
      )}
      {cameraCalOpen && (
        <CameraCalibration
          S={t}
          connected={fcu}
          send={reviewedSend}
          onClose={closeOverlay(setCameraCalOpen)}
        />
      )}
      {winchCalOpen && (
        <WinchCalibration
          S={t}
          connected={fcu}
          send={reviewedSend}
          onClose={closeOverlay(setWinchCalOpen)}
        />
      )}
      {overlayOpen && review && (
        <div className="dims-overlay" role="dialog" aria-label={review.label}>
          <div className="card dims review-dialog">{reviewBox}</div>
        </div>
      )}
    </div>
  );
}
/**
 * The MJPEG feed with what it is showing. An open stream that delivers no
 * frame never fires an error, so the old view stayed blank with no reason,
 * and Retry kept the same URL so it reloaded nothing.
 */
function CameraFeed({ url, topic, live, device }: {
  url: string; topic: string; live: boolean; device?: { ok: boolean; reason?: string };
}) {
  const [attempt, setAttempt] = useState(0),
    [state, setState] = useState<"waiting" | "playing" | "stalled" | "error">("waiting");
  const img = useRef<HTMLImageElement>(null);
  const src = `${url}&attempt=${attempt}`;
  // One late device report is not a frozen camera: warn after 2 s, not a blink.
  const badSince = useRef(0);
  const deviceBad = !!device && device.ok !== true;
  if (!deviceBad) badSince.current = 0;
  else if (!badSince.current) badSince.current = Date.now();
  const deviceDown = deviceBad && Date.now() - badSince.current > 2000;
  // Chrome keeps an MJPEG request open after its <img> leaves the page. Each
  // feed switch, retry or visit to another tab left one stream running; at
  // six the browser queued every request to the Pi, Stop and Land included.
  useLayoutEffect(() => {
    const element = img.current;
    return () => {
      if (element) element.src = "data:,";
    };
  }, [src, live, state === "error"]);
  useEffect(() => {
    setState("waiting");
    if (!live) return;
    const started = Date.now();
    const timer = window.setInterval(() => {
      if ((img.current?.naturalWidth ?? 0) > 0) setState((s) => (s === "error" ? s : "playing"));
      else if (Date.now() - started > 6000) setState((s) => (s === "waiting" ? "stalled" : s));
    }, 500);
    return () => window.clearInterval(timer);
  }, [src, live]);
  const message = !live
    ? "No live telemetry"
    : state === "error"
      ? "Video service not answering. Check the runtime, then retry."
      : state === "stalled"
        ? `No frames on ${topic}`
        : state === "waiting"
          ? `Opening ${topic}…`
          : deviceDown
            ? `Camera not reporting${device?.reason ? `: ${device.reason}` : ""}. Picture may be frozen.`
            : "";
  return (
    <>
      <div className="camera-frame">
        {live && state !== "error" && (
          <img ref={img} key={src} className="camera-feed" src={src}
            alt="Live aircraft camera" onError={() => setState("error")} />
        )}
        {message && <div className={`camera-overlay ${state === "playing" ? "warn" : ""}`}>{message}</div>}
      </div>
      <button onClick={() => setAttempt((a) => a + 1)}>Retry</button>
    </>
  );
}
function Datum({ label, text }: { label: string; text: string }) {
  return (
    <dl>
      <dt>{label}</dt>
      <dd>{text}</dd>
    </dl>
  );
}
function Field({
  label,
  text,
  placeholder,
  change,
}: {
  label: string;
  text: string;
  placeholder?: string;
  change: (text: string) => void;
}) {
  return (
    <label>
      {label}
      <input value={text} placeholder={placeholder} onChange={(event) => change(event.target.value)} />
    </label>
  );
}
