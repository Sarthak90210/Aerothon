// Mirrors the aggregator schema (docs/ARCHITECTURE.md §7.1).
// In production, GENERATE this from the Rust structs with ts-rs so it never drifts.

export interface Telemetry {
  mission: { selected: string | null; state: string; armed: boolean; mode: string; elapsed?: number };
  flight: {
    x: number; y: number; alt: number;
    gs?: number; roll_deg?: number; pitch_deg?: number; yaw_deg?: number;
  };
  gps: { lat: number; lon: number; sats: number; fix?: string };
  power: { volt: number; pct: number };
  nav: { front_m: number; centering_err: number; cmd_vx: number };
  percep: { start_qr: string; target_match: boolean; banner: boolean; redzone_visible: boolean };
  safety: { ready: boolean; fcu_connected?: boolean; ekf?: boolean; geofence?: string };
  checklist: Record<string, boolean>;
  scan?: { yaw_deg: number; ranges: (number | null)[] };
  gimbal?: { pitch_deg: number };
}

export interface Envelope {
  v: number;
  kind: "telemetry" | "event" | "ack" | "map";
  t: number;
  data: any;
}
