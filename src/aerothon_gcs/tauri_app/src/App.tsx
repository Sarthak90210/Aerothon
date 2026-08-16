import { useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";
import maplibregl, { type GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { drawHUD, drawMap, drawSlam, type OccGrid } from "./render";
import type { Telemetry, Envelope } from "./types";
import "./gcs.css";

const CL: [string, string][] = [
  ["takeoff", "Auto Takeoff (5m)"], ["start_qr", "Scan & Decode Start QR"],
  ["banner", "Corridor Banner Align"], ["corridor", "Corridor Nav & Avoidance"],
  ["target_id", "Target QR Search & Match"], ["drop", "Winch Drop & Ground Release"],
  ["return", "Corridor Return Navigation"], ["land", "Precision Landing at Origin"],
];
const STEP: Record<string, number> = {
  TAKEOFF: 0, GOTO_CORRIDOR: 1, CORRIDOR_NAV: 3, ENTER_ZONE: 3, SEARCH_QR: 4,
  WINCH_DROP: 5, RETURN: 6, RETURN_CORRIDOR: 6, LAND: 7,
};

export default function App() {
  const [S, setS] = useState<Telemetry | null>(null);
  const [log, setLog] = useState<string[]>([]);
  const [linked, setLinked] = useState(false);
  const [endpoint, setEndpoint] = useState("ws://127.0.0.1:8765");
  const [activeEndpoint, setActiveEndpoint] = useState("ws://127.0.0.1:8765");
  const [connectionNonce, setConnectionNonce] = useState(0);
  const [view, setView] = useState<"map" | "cam" | "slam">("map");
  const webSocket = useRef<WebSocket | null>(null);
  const inTauri = "__TAURI_INTERNALS__" in window;
  const mapHost = useRef<HTMLDivElement>(null);
  const geoMap = useRef<maplibregl.Map | null>(null);
  const gpsMarker = useRef<maplibregl.Marker | null>(null);
  const gpsTrail = useRef<[number, number][]>([]);
  const mapCentered = useRef(false);

  const hud = useRef<HTMLCanvasElement>(null);
  const map = useRef<HTMLCanvasElement>(null);
  const slam = useRef<HTMLCanvasElement>(null);
  const trail = useRef<[number, number][]>([]);
  const cells = useRef<Map<string, [number, number]>>(new Map());
  const grid = useRef<OccGrid | null>(null);
  const latest = useRef<Telemetry | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!inTauri) return;
    const un = listen<string>("ws", (e) => {
      setLinked(true);
      let env: Envelope; try { env = JSON.parse(e.payload); } catch { return; }
      if (env.kind === "telemetry") onTelemetry(env.data as Telemetry);
      else if (env.kind === "map") grid.current = env.data as OccGrid;
      else if (env.kind === "event") pushLog(`● ${env.data.msg}`);
      else if (env.kind === "ack") pushLog(`⤷ ack ${env.data.cmd}: ${env.data.result}`);
    });
    const unConn = listen<{ connected: boolean; endpoint: string }>("connection", (e) => {
      setLinked(e.payload.connected);
      setEndpoint(e.payload.endpoint);
      pushLog(e.payload.connected ? `● connected ${e.payload.endpoint}` : "○ disconnected");
    });
    let raf = 0;
    const loop = () => {
      if (hud.current) drawHUD(hud.current, latest.current);
      if (map.current) drawMap(map.current, latest.current, trail.current, cells.current, grid.current);
      if (slam.current) drawSlam(slam.current, latest.current, cells.current, grid.current);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => { un.then((f) => f()); unConn.then((f) => f()); cancelAnimationFrame(raf); };
  }, [inTauri]);

  // Browser build: communicate directly with the ROS WebSocket aggregator.
  // The Tauri desktop build continues to use its native command bridge.
  useEffect(() => {
    if (inTauri) return;
    let stopped = false;
    let retry: number | undefined;
    let raf = 0;
    const draw = () => {
      if (hud.current) drawHUD(hud.current, latest.current);
      if (map.current) drawMap(map.current, latest.current, trail.current, cells.current, grid.current);
      if (slam.current) drawSlam(slam.current, latest.current, cells.current, grid.current);
      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    const open = () => {
      if (stopped) return;
      const ws = new WebSocket(activeEndpoint);
      webSocket.current = ws;
      ws.onopen = () => {
        if (stopped || webSocket.current !== ws) return;
        setLinked(true);
        pushLog(`● connected ${activeEndpoint}`);
      };
      ws.onmessage = (e) => {
        if (stopped || webSocket.current !== ws) return;
        let env: Envelope; try { env = JSON.parse(String(e.data)); } catch { return; }
        if (env.kind === "telemetry") onTelemetry(env.data as Telemetry);
        else if (env.kind === "map") grid.current = env.data as OccGrid;
        else if (env.kind === "event") pushLog(`● ${(env.data as any).msg}`);
        else if (env.kind === "ack") {
          const d = env.data as any;
          pushLog(`⤷ ack ${d.cmd}: ${d.result}${d.reason ? ` · ${d.reason}` : ""}`);
        }
      };
      ws.onerror = () => {
        if (!stopped && webSocket.current === ws) ws.close();
      };
      ws.onclose = () => {
        if (stopped || webSocket.current !== ws) return;
        setLinked(false);
        retry = window.setTimeout(open, 2000);
      };
    };
    open();
    return () => {
      stopped = true;
      cancelAnimationFrame(raf);
      if (retry !== undefined) window.clearTimeout(retry);
      const ws = webSocket.current;
      if (ws) {
        ws.onclose = null;
        ws.close();
        if (webSocket.current === ws) webSocket.current = null;
      }
    };
  }, [activeEndpoint, connectionNonce, inTauri]);

  useEffect(() => {
    if (!mapHost.current) return;
    const gm = new maplibregl.Map({
      container: mapHost.current,
      center: [149.1652, -35.36324],
      zoom: 18,
      attributionControl: { compact: true },
      style: {
        version: 8,
        sources: {
          satellite: {
            type: "raster",
            // Satellite arena tiles are bundled for offline competition use.
            tiles: ["/satellite/{z}/{x}/{y}.jpg"],
            tileSize: 256,
            minzoom: 14,
            maxzoom: 19,
            attribution: "Tiles © Esri — Esri, Maxar, Earthstar Geographics, GIS Community",
          },
        },
        layers: [{ id: "satellite", type: "raster", source: "satellite" }],
      },
    });
    gm.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-right");
    gm.on("load", () => {
      gm.addSource("flight-trail", {
        type: "geojson",
        data: { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: gpsTrail.current } },
      });
      gm.addLayer({
        id: "flight-trail", type: "line", source: "flight-trail",
        paint: { "line-color": "#e8eef5", "line-width": 4, "line-opacity": 0.9 },
      });
    });
    geoMap.current = gm;
    gpsMarker.current = new maplibregl.Marker({ color: "#d47a72" });
    return () => { gpsMarker.current?.remove(); gm.remove(); geoMap.current = null; };
  }, []);

  function onTelemetry(d: Telemetry) {
    latest.current = d;
    trail.current.push([d.flight.x, d.flight.y]);
    if (trail.current.length > 2000) trail.current.shift();
    if (Number.isFinite(d.gps?.lat) && Number.isFinite(d.gps?.lon) &&
        Math.abs(d.gps.lat) > 0.0001 && Math.abs(d.gps.lon) > 0.0001) {
      const ll: [number, number] = [d.gps.lon, d.gps.lat];
      gpsTrail.current.push(ll);
      if (gpsTrail.current.length > 2000) gpsTrail.current.shift();
      gpsMarker.current?.setLngLat(ll).addTo(geoMap.current!);
      if (!mapCentered.current) {
        geoMap.current?.jumpTo({ center: ll, zoom: 19 });
        mapCentered.current = true;
      }
      const src = geoMap.current?.getSource("flight-trail") as GeoJSONSource | undefined;
      src?.setData({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: gpsTrail.current } });
    }
    const sc = (d as any).scan;
    if (sc && sc.ranges) {
      const R = sc.ranges, n = R.length;
      for (let k = 0; k < n; k++) {
        const r = R[k]; if (r == null) continue;
        const a = -Math.PI + 2 * Math.PI * k / n;
        const ex = d.flight.x + r * Math.cos(a), ey = d.flight.y + r * Math.sin(a);
        cells.current.set(Math.round(ex / 0.15) + "," + Math.round(ey / 0.15), [ex, ey]);
      }
      if (cells.current.size > 15000) cells.current.clear();
    }
    setS(d);
  }

  function pushLog(l: string) {
    setLog((x) => [...x.slice(-150), `${new Date().toLocaleTimeString()}  ${l}`]);
    setTimeout(() => logRef.current?.scrollTo(0, 1e9), 0);
  }
  async function send(cmd: string, args: any = {}, danger = false) {
    if (danger && !confirm(`Confirm command: ${cmd.toUpperCase()}?`)) return;
    try {
      if (inTauri) await invoke("send_command", { cmd, args });
      else {
        const ws = webSocket.current;
        if (!ws || ws.readyState !== WebSocket.OPEN) throw new Error("drone WebSocket not connected");
        ws.send(JSON.stringify({
          v: 1, kind: "command", t: Date.now() / 1000,
          data: { cmd_id: crypto.randomUUID(), cmd, args, confirm: true },
        }));
      }
      pushLog(`→ ${cmd}`);
    }
    catch (e) { pushLog(`✗ ${cmd}: ${e}`); }
  }
  async function connect() {
    try {
      if (inTauri) await invoke("set_endpoint", { endpoint });
      else {
        setActiveEndpoint(endpoint.trim().replace(/\/$/, ""));
        // Allow CONNECT to force a clean retry even when the URL is unchanged.
        setConnectionNonce((value) => value + 1);
      }
      setLinked(false); pushLog(`→ connect ${endpoint}`);
    }
    catch (e) { pushLog(`✗ connection: ${e}`); }
  }

  const videoUrl = (() => {
    try {
      const u = new URL(endpoint);
      u.protocol = u.protocol === "wss:" ? "https:" : "http:";
      u.port = "8080"; u.pathname = "/stream"; u.search = "?topic=/percep/qr/annotated&type=mjpeg";
      return u.toString();
    } catch { return ""; }
  })();

  const f = S?.flight, m = S?.mission, p = S?.percep, sa = S?.safety;
  const cur = STEP[m?.state ?? ""] ?? -1;
  const pill = (g: boolean | undefined, a: string, b: string, inv = false) =>
    <span className={`pill ${g ? "ok" : inv ? "bad" : "warn"}`}>{g ? a : b}</span>;

  return (
    <div className="gcs">
      <header>
        <div className="brand"><span className="logo-dot" /> AEROTHON <small>GCS</small></div>
        <span className="badge mode">{m?.mode || "GUIDED"}</span>
        <span className={`badge ${m?.armed ? "armed" : "disarmed"}`}>{m?.armed ? "ARMED" : "DISARMED"}</span>
        <span className={`badge ${sa?.fcu_connected ? "connected" : "disconnected"}`}>
          FCU {sa?.fcu_connected ? "CONNECTED" : "DISCONNECTED"}
        </span>
        <span className="badge">{m?.state || "STANDBY"}</span>
        <div className="view-nav">
          <button className={`view-btn ${view === "map" ? "active" : ""}`} onClick={() => setView("map")}>Flight Map</button>
          <button className={`view-btn ${view === "cam" ? "active" : ""}`} onClick={() => setView("cam")}>Video</button>
          <button className={`view-btn ${view === "slam" ? "active" : ""}`} onClick={() => setView("slam")}>SLAM</button>
        </div>
        <div className="spacer" />
        <div className="stat"><span className="k">GPS</span><span className="v mono">{(S as any)?.gps?.fix || "—"} · {S?.gps?.sats || 0}</span></div>
        <div className="stat"><span className="k">Pos</span><span className="v mono">{f ? `${f.x.toFixed(1)}, ${f.y.toFixed(1)}` : "0, 0"}</span></div>
        <div className="stat"><span className="k">EKF</span><span className="v">{(sa as any)?.ekf ? "OK" : "—"}</span></div>
        <div className="stat"><span className="k">Time</span><span className="v mono">{(m as any)?.elapsed?.toFixed?.(1) || "0.0"}s</span></div>
        <div className="stat connection-control">
          <span className="k">GCS WebSocket · {linked ? "CONNECTED" : "DISCONNECTED"}</span>
          <div className="endpoint-row">
            <input aria-label="Drone WebSocket endpoint" value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") connect(); }} />
            <button onClick={connect}>CONNECT</button>
          </div>
        </div>
        <div className="batt-container">
          <div className="stat"><span className="k">Batt</span><span className="v mono">{S ? S.power.volt.toFixed(1) : 0}V</span></div>
          <div className="batt-bar"><div className="batt-fill" style={{ width: `${S?.power.pct || 0}%` }} /></div>
          <span className="batt-text mono">{S?.power.pct || 0}%</span>
        </div>
      </header>

      <main>
        {/* LEFT RAIL — HUD on top, all telemetry values stacked below (Mission Planner style) */}
        <aside className="rail">
          <div className="card hud-card">
            <div className="hd">Primary Flight Display <span className="tag">HUD</span></div>
            <div className="hud-body"><canvas ref={hud} width={380} height={300} /></div>
          </div>
          <div className="card values">
            <div className="sec">Flight Data</div>
            <div className="tele">
              <Cell k="Altitude" v={f?.alt?.toFixed(2)} u="m" />
              <Cell k="Ground Speed" v={(f as any)?.gs?.toFixed(2)} u="m/s" />
              <Cell k="Heading" v={Math.round((f as any)?.yaw_deg || 0)} u="°" />
              <Cell k="Front Lidar" v={S?.nav.front_m?.toFixed(2)} u="m" />
              <Cell k="Roll / Pitch" v={f ? `${(f as any).roll_deg?.toFixed(0)} / ${(f as any).pitch_deg?.toFixed(0)}` : "—"} small />
              <Cell k="Centering" v={(S?.nav.centering_err || 0).toFixed(2)} u="m" small />
            </div>
            <div className="sec">Perception &amp; Interlock</div>
            <div className="kv"><span className="dim">Start QR</span><span className="mono" style={{ color: "var(--accent)" }}>{p?.start_qr || "—"}</span></div>
            <div className="kv"><span className="dim">Target Match</span>{pill(p?.target_match, "MATCHED", "SEARCHING")}</div>
            <div className="kv"><span className="dim">Green Banner</span>{pill(p?.banner, "ALIGNED", "SCANNING")}</div>
            <div className="kv"><span className="dim">Red Zone</span>{pill(!p?.redzone_visible, "CLEAR", "RESTRICTED", true)}</div>
            <div className="kv"><span className="dim">Interlock</span>{pill(sa?.ready, "GO", "STANDBY")}</div>
            <div className="sec">Mission Sequence</div>
            <div className="checklist">
              {CL.map(([k, label], i) => {
                const done = S?.checklist[k]; const active = i === cur && !done;
                return <div key={k} className={`ci ${done ? "done" : ""} ${active ? "active" : ""}`}>
                  <span className="ico">{done ? "✓" : active ? "●" : ""}</span>{label}</div>;
              })}
            </div>
          </div>
        </aside>

        {/* RIGHT STAGE — big map / SLAM / video, switched by the header view tabs */}
        <section className="card stage">
          <div className="hd">
            {view === "cam" ? "Continuous Camera Feed" : view === "slam" ? "SLAM Occupancy & Costmap" : "Flight Map · Live"}
            <span className="tag">{view === "cam" ? "web_video_server MJPEG" : view === "slam" ? "slam_toolbox · RPLidar C1" : "Satellite · live GPS track"}</span>
          </div>
          <div className="stage-body">
            <div ref={mapHost} className="maplibre-host" style={{ display: view === "map" ? "block" : "none" }} />
            <canvas ref={slam} width={960} height={620} style={{ display: view === "slam" ? "block" : "none" }} />
            {view === "cam" && (
              <div className="cam-wrap">
                <img src={videoUrl} alt="Live camera feed"
                  onError={(e) => { (e.target as HTMLElement).style.display = "none"; }} />
                <div className="cam-tag tl">REC · {videoUrl || "set drone endpoint"}</div>
                <div className="cam-tag br">OpenCV QR + HSV banner</div>
                <div className="gimbal-control">
                  <span>CAMERA SERVO · {S?.gimbal?.pitch_deg?.toFixed(0) ?? 0}°</span>
                  <button onClick={() => send("gimbal_pitch", { degrees: 0 })}>FORWARD</button>
                  <button onClick={() => send("gimbal_pitch", { degrees: -45 })}>45° DOWN</button>
                  <button onClick={() => send("gimbal_pitch", { degrees: -90 })}>DOWN</button>
                </div>
              </div>
            )}
          </div>
        </section>
      </main>

      <footer>
        <div className="btns">
          <button className="primary" onClick={() => send("set_mode", { mode: "GUIDED" })}>GUIDED</button>
          <button disabled={!sa?.ready} onClick={() => send("arm", {}, true)}>ARM</button>
          <button disabled={!sa?.ready} onClick={() => send("takeoff", { alt: 5.0 })}>TAKEOFF</button>
          <button disabled={!sa?.ready} className="primary" onClick={() => send("start_mission", {}, true)}>START M2</button>
          <button onClick={() => send("disarm", {}, true)}>DISARM</button>
          <button className="warn" onClick={() => send("land", {})}>LAND</button>
          <button className="warn" onClick={() => send("set_mode", { mode: "RTL" }, true)}>RTL</button>
          <button className="danger" onClick={() => send("abort", {}, true)}>ABORT</button>
        </div>
        <div className="log mono" ref={logRef}>{log.map((l, i) => <div key={i}>{l}</div>)}</div>
      </footer>
    </div>
  );
}

function Cell({ k, v, u, small }: { k: string; v: any; u?: string; small?: boolean }) {
  return <div className="cell"><div className="k">{k}</div>
    <div className="v mono" style={small ? { fontSize: 14 } : undefined}>{v ?? "—"}{u && <small> {u}</small>}</div></div>;
}
