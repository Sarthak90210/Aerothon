import { useEffect } from "react";
import type { Telemetry } from "./types";

// The LD06 is wherever its bracket put it, and its driver may scan either
// way; every scan consumer reads a beam's bearing off the nose, CCW. Two
// boxes measure the mount: one ahead of the nose, one to port. The aircraft
// sends what it measured to scan_mount, which applies it at once and keeps
// it across a restart (gcs_aggregator/lidar_calibration.py).

type Props = {
  S: Telemetry | null;
  connected: boolean;
  send: (cmd: string, args?: any, danger?: boolean) => void;
  onClose: () => void;
};

const fmt = (p: [number, number] | null | undefined) =>
  p
    ? `${p[0] >= 0 ? "+" : ""}${p[0].toFixed(1)}° at ${p[1].toFixed(2)} m`
    : "—";

// Top view, nose up; bearings CCW from the nose, so +90 (port) is left.
function TopView({
  body,
  raw,
}: {
  body?: [number, number] | null;
  raw?: [number, number] | null;
}) {
  const R = 90,
    scale = R / 2.5; // 2.5 m to the edge
  const dot = (p: [number, number] | null | undefined, cls: string) => {
    if (!p) return null;
    const r = Math.min(p[1], 2.5) * scale,
      b = (p[0] * Math.PI) / 180;
    return (
      <circle
        className={cls}
        cx={100 - r * Math.sin(b)}
        cy={100 - r * Math.cos(b)}
        r={6}
      />
    );
  };
  return (
    <svg
      className="lidar-view"
      viewBox="0 0 200 200"
      aria-label="Nearest lidar return, top view"
    >
      <circle cx="100" cy="100" r={1 * scale} className="lidar-ring" />
      <circle cx="100" cy="100" r={2 * scale} className="lidar-ring" />
      <line x1="100" y1="100" x2="100" y2="10" className="lidar-axis" />
      <line x1="100" y1="100" x2="10" y2="100" className="lidar-axis" />
      <text x="104" y="16" className="lidar-lbl">
        nose 0°
      </text>
      <text x="10" y="94" className="lidar-lbl">
        port +90°
      </text>
      <polygon points="100,86 92,108 108,108" className="lidar-craft" />
      {dot(raw, "lidar-raw")}
      {dot(body, "lidar-body")}
    </svg>
  );
}

export default function LidarCalibration({
  S,
  connected,
  send,
  onClose,
}: Props) {
  const cal = S?.lidar_cal;
  const armed = !connected || S?.mission?.armed !== false;
  const res = cal?.result ?? null;
  const applied = cal?.applied ?? null;
  const live = Boolean(cal?.raw_fresh);
  // Escape closes the dialog, as the arena panel does.
  useEffect(() => {
    const key = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [onClose]);

  return (
    <div className="dims-overlay" role="dialog" aria-label="Lidar calibration">
      <div className="card dims lidar">
        <div className="hd">
          Lidar calibration
          <span className={`tag ${live ? "ok" : ""}`}>
            {live ? "raw scan live" : "no raw scan — lidar driver not running"}
          </span>
          <button className="dims-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="lidar-body">
          <ol className="lidar-steps">
            <li>
              Disarmed, props off. Clear everything within 2 m of the aircraft.
            </li>
            <li>
              Hold a box ~1 m <b>straight ahead of the nose</b>, square to the
              aircraft.
              <div className="lidar-step-row">
                <span>Nearest (raw): {fmt(cal?.raw_nearest)}</span>
                <button
                  disabled={armed || !live}
                  onClick={() => send("lidar_cal_capture", { where: "ahead" })}
                >
                  Capture ahead
                </button>
                <span className="lidar-cap">{fmt(cal?.captures?.ahead)}</span>
              </div>
            </li>
            <li>
              Move it ~1 m <b>to port (left)</b>, square to the aircraft.
              <div className="lidar-step-row">
                <span>Nearest (raw): {fmt(cal?.raw_nearest)}</span>
                <button
                  disabled={armed || !live}
                  onClick={() => send("lidar_cal_capture", { where: "port" })}
                >
                  Capture port
                </button>
                <span className="lidar-cap">{fmt(cal?.captures?.port)}</span>
              </div>
            </li>
            <li>
              Apply, then check: the box ahead must read about 0°, to port about
              +90°, in the corrected scan.
            </li>
          </ol>
          <div className="lidar-side">
            <TopView body={cal?.body_nearest} raw={cal?.raw_nearest} />
            <div className="lidar-legend">
              <span className="sw body" /> corrected (/scan){" "}
              <span className="sw raw" /> raw (/scan_raw)
            </div>
            <div>
              Corrected nearest: <b>{fmt(cal?.body_nearest)}</b>
            </div>
          </div>
        </div>
        <div className="dims-actions">
          <span className="dims-note">
            {res
              ? res.ok
                ? `Measured: mount yaw ${res.yaw_deg >= 0 ? "+" : ""}${res.yaw_deg}°, ` +
                  `${res.mirrored ? "driver scans clockwise (mirrored)" : "counter-clockwise"}, ` +
                  `captures ${res.error_deg}° from square.`
                : res.reason
              : "Capture both boxes to measure the mount."}
            {applied && (
              <>
                <br />
                In force: yaw {applied.yaw_deg >= 0 ? "+" : ""}
                {applied.yaw_deg}°,{" "}
                {applied.mirrored ? "mirrored" : "counter-clockwise"} —{" "}
                {applied.source}
                {applied.reason ? ` (${applied.reason})` : ""}
              </>
            )}
            {armed && (
              <>
                <br />
                Disarm to calibrate.
              </>
            )}
          </span>
          <button onClick={() => send("lidar_cal_reset")} disabled={armed}>
            Start again
          </button>
          <button
            className="primary"
            disabled={armed || !res?.ok}
            onClick={() => send("lidar_cal_apply", {}, true)}
          >
            APPLY TO AIRCRAFT
          </button>
        </div>
      </div>
    </div>
  );
}
