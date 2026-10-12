// Mirrors the aggregator schema (docs/ARCHITECTURE.md §7.1).
// In production, GENERATE this from the Rust structs with ts-rs so it never drifts.

// One line of the Q27 arming interlock (gcs_aggregator/readiness.py).
export interface ReadinessItem {
  key: string;
  label: string;
  ok: boolean;
  value: unknown;
  reason: string;
}

export interface Telemetry {
  mission: {
    selected: string | null; state: string; armed: boolean; mode: string;
    elapsed?: number;
    // Delivery accuracy is 15 rulebook marks and was measured nowhere; it is
    // carried as a NUMBER so the panel can compare and threshold it, not just
    // print a sentence.
    delivery_offset_m?: number | null;
    landing_precision?: string | null;
    result?: string | null;
    result_reason?: string | null;
  };
  flight: {
    x: number; y: number; alt: number;
    gs?: number; roll_deg?: number; pitch_deg?: number; yaw_deg?: number;
  };
  gps: { lat: number; lon: number; sats: number; fix?: string };
  power: { volt: number; pct: number };
  nav: { front_m: number; centering_err: number; cmd_vx: number };
  percep: {
    start_qr: string; target_match: boolean; banner: boolean;
    redzone_visible: boolean;
    // Tri-state. "CLEAR" means the camera looked at the ground and saw none;
    // "NOT_VISIBLE" means it could not see the ground at all. The old boolean
    // reported both as safe.
    redzone_status?: "UNKNOWN" | "NOT_VISIBLE" | "CLEAR" | "RED";
    redzone_reason?: string;
    redzone_exclusions?: number[][];
    redzone_area_m2?: number;
    // Square on: perpendicular to the banner's FACE, measured by the lidar.
    // Distinct from `banner`, which only says the nose points at it. null
    // means not measured -- never render it as zero.
    square_ok?: boolean | null;
    square_angle_deg?: number | null;
    square_standoff_m?: number | null;
    square_reason?: string;
  };
  safety: {
    ready: boolean; fcu_connected?: boolean; ekf?: boolean; geofence?: string;
    ready_items?: ReadinessItem[];
    ready_reasons?: string[];
    ready_waived?: string[];
  };
  checklist: Record<string, boolean>;
  scan?: { yaw_deg: number; ranges: (number | null)[] };
  scans?: ScanRow[];
  gimbal?: { pitch_deg: number };
  // Arena dimensions (mission_bt/arena_dimensions.py): the field list, the
  // presets, and what mission_bt reports it actually applied.
  dimension_fields?: DimensionField[];
  dimension_presets?: { builtin: Record<string, Dimensions>; saved: Record<string, Dimensions> };
  arena_dimensions?: {
    sent: Dimensions | null; applied: Dimensions | null;
    params?: Record<string, unknown> | null; ok?: boolean; reason: string;
  } | null;
  // Lidar calibration mode (gcs_aggregator/lidar_calibration.py): bearings
  // in degrees CCW from the nose (corrected) or the lidar's own 0 (raw).
  lidar_cal?: {
    raw_fresh: boolean;
    raw_nearest: [number, number] | null;
    body_nearest: [number, number] | null;
    captures: { ahead: [number, number] | null; port: [number, number] | null };
    result: { yaw_deg: number; mirrored: boolean; error_deg: number;
              ok: boolean; reason: string } | null;
    applied: { yaw_deg: number; mirrored: boolean; source: string;
               reason: string } | null;
  };
}

// group -> field -> value. Lengths in metres; the two choice fields are strings.
export type Dimensions = Record<string, Record<string, number | string>>;

export interface DimensionField {
  group: string; key: string; label: string;
  default: number; min: number; max: number;
  // What the algorithms do with it; null means recorded only.
  used_by: string | null;
}

// One observation the aircraft made: a marker it decoded, a banner it read, or
// something it looked at and REFUSED. De-duplicated by the aggregator, so a
// marker held in frame for 200 frames is one row with count 200 -- the count
// separates a solid read from a single-frame blip.
export interface ScanRow {
  key: string;
  seq: number;
  kind: "qr" | "banner";
  // What was read. Empty on a rejection, where `reason` carries the detail.
  payload: string;
  // Decoding is not matching. Only a payload equal to the delivery target
  // named by the start QR is a match, and only a match is tagged.
  matched: boolean;
  status: "DECODED" | "MATCHED" | "IDENTIFIED" | "REJECTED";
  reason: string;
  // Which lettering path read it: "brightness" or "stroke". A rescued read
  // should look different from a clean one.
  via: string;
  stage: string;
  t: number;
  t_last: number;
  count: number;
}

export interface Envelope {
  v: number;
  kind: "telemetry" | "event" | "ack" | "map";
  t: number;
  data: any;
}
