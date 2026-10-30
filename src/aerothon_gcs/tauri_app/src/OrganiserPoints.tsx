import { useState } from "react";
import type { Telemetry } from "./types";
import { parseLatLon } from "./organiser";

// The organisers' six fence points first (required), then home and the two
// corridors' ends (optional: without them the aircraft finds the corridors
// with its camera and lidar, as before). Each point is typed as
// "lat, lon", or recorded: stand the aircraft on the spot and press Record,
// and the aggregator averages its GPS for 5 s (3D fix, 8+ satellites).
// Apply sends the fence (outline of the six), the zone (the four corners)
// and the course points to the aircraft.
const FENCE_ORDER = ["fence_back_left", "fence_back_right", "zone_1", "zone_2", "zone_3", "zone_4"];

type Props = {
  t: Telemetry | null;
  busy: boolean;
  fcu: boolean;
  perform: (cmd: string, args?: Record<string, unknown>) => void;
  review: (cmd: string, args: Record<string, unknown>, danger: boolean, label?: string) => void;
};

export default function OrganiserPoints({ t, busy, fcu, perform, review }: Props) {
  const op = t?.organiser_points;
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [paste, setPaste] = useState("");
  const [pasteError, setPasteError] = useState("");
  if (!op) return <p className="view-note">Organiser points: waiting for the aircraft link.</p>;
  const disarmed = t?.mission.armed === false;
  const recording = op.recording;
  const missing = op.slots.filter((s) => s.required && !op.points[s.key]);
  const fillFence = () => {
    const lines = paste.trim().split("\n").filter(Boolean);
    const pts = lines.map(parseLatLon);
    if (pts.length !== 6 || pts.some((p) => p === null)) {
      setPasteError("Paste six lines of lat, lon: behind-left, behind-right, then the four corners");
      return;
    }
    setPasteError("");
    pts.forEach((p, i) => perform("set_point", { slot: FENCE_ORDER[i], ...p! }));
  };
  return (
    <div className="organiser-points">
      <p className="view-note">
        The six fence points are required; the rest are optional. Type
        "lat, lon" and Set, or stand the aircraft on the spot and Record
        (5 s average, 3D fix and 8+ satellites).
      </p>
      {op.slots.map((slot, i) => {
        const p = op.points[slot.key];
        const draft = drafts[slot.key] ?? "";
        const parsed = draft.trim() ? parseLatLon(draft) : null;
        const isRecording = recording?.slot === slot.key;
        return (
          <div key={slot.key} className="point-row">
            {i === 6 && <h4>Optional: home and corridors</h4>}
            <label>
              {slot.label}
              {slot.required ? " *" : ""}
              <input
                value={draft}
                placeholder={p ? `${p.lat.toFixed(7)}, ${p.lon.toFixed(7)}` : "lat, lon"}
                onChange={(e) => setDrafts({ ...drafts, [slot.key]: e.target.value })}
              />
            </label>
            <button
              disabled={!fcu || busy || !disarmed || !parsed}
              onClick={() => {
                perform("set_point", { slot: slot.key, ...parsed! });
                setDrafts({ ...drafts, [slot.key]: "" });
              }}
            >
              Set
            </button>
            <button
              disabled={!fcu || busy || Boolean(recording) || t?.gps?.fix !== "3D"}
              onClick={() => perform("record_point", { slot: slot.key })}
            >
              {isRecording ? `Recording ${recording!.elapsed_s.toFixed(0)} s` : "Record here"}
            </button>
            <button
              disabled={!fcu || busy || !disarmed || !p}
              onClick={() => perform("set_point", { slot: slot.key, clear: true })}
            >
              Clear
            </button>
            <span className="view-note">
              {p
                ? p.source === "recorded"
                  ? `recorded (${p.samples} fixes, spread ${p.spread_m?.toFixed(1)} m)`
                  : "typed"
                : slot.required
                  ? "not set"
                  : "not used"}
            </span>
          </div>
        );
      })}
      {op.last && (
        <p className="view-note">
          {op.slots.find((s) => s.key === op.last!.slot)?.label}: {op.last.ok ? op.last.reason : `not recorded: ${op.last.reason}`}
        </p>
      )}
      <label>
        Paste the six fence points (behind-left, behind-right, corners 1-4)
        <textarea rows={6} value={paste} onChange={(e) => setPaste(e.target.value)} />
      </label>
      <button disabled={!fcu || busy || !disarmed || !paste.trim()} onClick={fillFence}>
        Fill fence points
      </button>
      {pasteError && <p className="view-note">{pasteError}</p>}
      <button
        disabled={!fcu || busy || !disarmed || missing.length > 0}
        onClick={() => review("apply_organiser_points", {}, true, "apply organiser points")}
      >
        Apply organiser points
      </button>
      <p className="view-note">
        {missing.length
          ? `Not set: ${missing.map((s) => s.label).join(", ")}`
          : op.applied
            ? `Applied: fence of ${op.applied.fence} points, search inside the four corners` +
              `${op.applied.home ? ", home" : ""}${op.applied.entry ? ", entry corridor" : ""}` +
              `${op.applied.exit ? ", exit corridor" : ""}.`
            : "Ready to apply."}
      </p>
    </div>
  );
}
