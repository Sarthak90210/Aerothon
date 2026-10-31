import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  endpoint,
  videoUrl,
  freshFcu,
  startAllowed,
  startBlockReason,
  taskCommand,
  commandEnvelope,
  acknowledgement,
  commandId,
  reviewAllowed,
  tasks,
} from "../src/runtime.ts";
import { validateDraft } from "../src/arenaForm.ts";
const schema = JSON.parse(
  readFileSync(new URL("../src/arenaSchema.json", import.meta.url)),
);

test('HTTP intranet browsers without randomUUID can still send unique command IDs', () => {
  const provider = { getRandomValues: bytes => { bytes.set(Array.from({length:16}, (_,i) => i)); return bytes; } };
  assert.equal(commandId(provider), '00010203-0405-4607-8809-0a0b0c0d0e0f');
  assert.equal(commandId({ ...provider, randomUUID: () => 'secure-context-id' }), 'secure-context-id');
  assert.throws(() => commandId({}));
});
const ready = () => ({
  mission: { state: "IDLE", mode: "GUIDED", armed: false },
  safety: { ready: true, fcu_connected: true },
  runtime_health: {fresh:true},
  sample_age_s: { state: 0.1, readiness: 0.1 },
});

test("browser tasks use the shared production supervisor registry", () => {
  const source = readFileSync(new URL("../../../aerothon_runtime/aerothon_runtime/contracts.py", import.meta.url),"utf8");
  for(const task of tasks) {
    assert.ok(source.includes(`'${task.id}':`));
    const c=taskCommand(task.id,'stow',{height:5});
    assert.equal(c.cmd,'start'); assert.equal(c.args.task, task.id);
  }
  assert.deepEqual(taskCommand('mechanism','release'), {cmd:'start',args:{task:'mechanism',params:{action:'release'}}});
  assert.throws(()=>taskCommand('manual_joystick','stow'));
  assert.throws(()=>taskCommand('mechanism','unsupported'));
});
test("flight starts require fresh FCU and readiness, exclusive execution", () => {
  const t = ready();
  assert.equal(startAllowed(t, true, "mission"), true);
  assert.equal(startAllowed(t, false, "mission"), false);
  for (const key of ["state", "readiness"]) {
    const stale = ready();
    stale.sample_age_s[key] = 3;
    assert.equal(startAllowed(stale, true, "mission"), false);
  }
  for (const phase of ["STARTING", "TAKEOFF", "SEARCH", "RETURN", "LAND"]) {
    t.execution = {task:'mission',state:'Running',stage:phase};
    assert.equal(startAllowed(t, true, "mission"), false);
  }
  delete t.execution;
  t.runtime_health.fresh=false;
  assert.equal(startAllowed(t, true, "mission"), false);
  assert.equal(freshFcu(null), false);
  assert.equal(freshFcu({}), false);
});
test("mechanism bench tasks do not require flight readiness and never implicitly arm", () => {
  const t = ready();
  t.safety.ready = false;
  t.mission.mode = "STABILIZE";
  assert.equal(startAllowed(t, true, "mechanism"), false);
  t.devices={winch_actuator:{ok:true}};
  assert.equal(startAllowed(t, true, "mechanism"), true);
  t.mission.armed = true;
  assert.equal(startAllowed(t, true, "mechanism"), false);
  assert.equal(taskCommand("mechanism", "lower").cmd, "start");
});
test("acknowledgement cannot claim physical completion", () => {
  assert.equal(
    acknowledgement({ cmd_id: "id", cmd: "winch", result: "accepted" }).state,
    "Accepted",
  );
  assert.equal(
    acknowledgement({ cmd_id: "id", cmd: "winch", result: "rejected" }).state,
    "Failed",
  );
  assert.equal(
    acknowledgement({ cmd_id: "id", cmd: "winch", result: "completed" }).state,
    "Outcome unknown",
  );
});

test("review confirmation rechecks arming, takeoff, disarm and mechanism conditions", () => {
  const t = ready();
  assert.equal(reviewAllowed(t, true, "takeoff", { alt: NaN }), false);
  assert.equal(reviewAllowed(t, true, "takeoff", { alt: 5 }), true);
  t.mission.armed = true;
  assert.equal(reviewAllowed(t, true, "winch", { action: "release" }), false);
  assert.equal(reviewAllowed(t, true, "disarm", {}), false);
  t.safety.on_ground = true;
  t.sample_age_s.extended_state = 0.1;
  assert.equal(reviewAllowed(t, true, "disarm", {}), true);
  t.sample_age_s.state = 4;
  assert.equal(reviewAllowed(t, true, "arm", {}), false);
  assert.equal(reviewAllowed(t, true, "abort", {}), true);
  assert.equal(reviewAllowed(null, true, "abort", {}), true);
});
test("changed addresses are shared by telemetry and video with no embedded credentials", () => {
  assert.equal(
    endpoint(" ws://192.168.0.101:8765/ "),
    "ws://192.168.0.101:8765",
  );
  assert.equal(
    videoUrl("ws://192.168.0.100:8765", "/percep/overlay"),
    "/video/stream?topic=%2Fpercep%2Foverlay&type=mjpeg",
  );
  assert.throws(() => endpoint("http://localhost:8899"));
  assert.throws(() => endpoint("ws://user:password@localhost:8765"));
});
test("all twenty-three production arena dimensions and built-in presets validate offline", () => {
  // Twenty, the clarified exit-corridor obstacle reach, and from the field
  // PDF (25 Oct) the ground banner's own height and the obstacle height.
  assert.equal(schema.fields.length, 23);
  assert.ok(schema.fields.some((f) => f.group === "obstacle" && f.key === "reach_frac"));
  assert.ok(schema.fields.some((f) => f.group === "obstacle" && f.key === "height_m"));
  assert.ok(schema.fields.some((f) => f.group === "banner" && f.key === "ground_height_m"));
  assert.deepEqual(validateDraft(schema.defaults, schema.fields), []);
  for (const preset of Object.values(schema.presets))
    assert.deepEqual(validateDraft(preset, schema.fields), []);
  const d = structuredClone(schema.defaults);
  d.corridor.nav_height_m = d.corridor.wall_height_m;
  assert.ok(validateDraft(d, schema.fields).some((s) => s.includes("walls")));
  d.payload.mass_kg = "";
  assert.ok(
    validateDraft(d, schema.fields).some((s) => s.includes("Payload mass")),
  );
  d.banner.border_m = 1;
  assert.ok(validateDraft(d, schema.fields).some((s) => s.includes("panel")));
  // The field PDF's 6 ft boards: an 8 ft navigation height puts the lidar
  // over them (arena_dimensions.validate refuses it too).
  const field = structuredClone(schema.presets["AeroTHON 2026 Track 1 field (organiser PDF)"]);
  assert.deepEqual(validateDraft(field, schema.fields), []);
  field.corridor.nav_height_m = 2.4384;
  assert.ok(validateDraft(field, schema.fields).some((s) => s.includes("lidar sees the obstacles")));
});
test("a blocked start names its reason, and the reason agrees with startAllowed", () => {
  const t = ready();
  assert.equal(startBlockReason(t, true, "mission"), "");
  assert.match(startBlockReason(t, false, "mission"), /No live telemetry/);
  t.execution = {task:'slam',state:'Running'};
  assert.match(startBlockReason(t, true, "qr"), /SLAM mapping is running/);
  delete t.execution;
  t.devices = {lidar:{ok:false,reason:'no scans for 3 s'}};
  assert.equal(startBlockReason(t, true, "slam"), "The lidar is unavailable (lidar: no scans for 3 s).");
  assert.equal(startAllowed(t, true, "slam"), false);
  t.safety.ready = false;
  assert.match(startBlockReason(t, true, "banner"), /readiness interlock is blocked/);
  assert.match(startBlockReason(t, true, "mechanism"), /Winch feedback is unavailable/);
});
test("manual mode runs no tasks and says so instead of a missing service", () => {
  const t = ready();
  t.runtime_mode = "manual";
  delete t.runtime_health;
  for (const task of tasks) {
    assert.match(startBlockReason(t, true, task.id), /^Manual mode:/);
    assert.equal(startAllowed(t, true, task.id), false);
  }
  t.runtime_mode = "mission";
  assert.match(startBlockReason(t, true, "mission"), /execution service is not reporting/);
});
test("a flight start waiting on a device says what the device measured", () => {
  const t = ready();
  t.devices = {identity:{ok:true}, lidar:{ok:true}, clock:{ok:true}, camera_actuator:{ok:true},
    camera:{ok:false, reason:'', vehicle_hz:8.7, required_vehicle_hz:10}};
  assert.equal(startBlockReason(t, true, "banner"),
    "Waiting for devices: camera at 8.7 Hz in vehicle time, 10 Hz required.");
  assert.equal(startAllowed(t, true, "banner"), false);
  t.devices.camera = {ok:true};
  assert.equal(startBlockReason(t, true, "banner"), "");
  assert.match(startBlockReason(t, true, "delivery_here"), /winch actuator is not reported/);
});

test("the aircraft's waived actuators block neither mission but still block other tasks", () => {
  const t = ready();
  const waived = ["mission", "mission_skip_corridor"];
  t.devices = {identity:{ok:true}, camera:{ok:true}, lidar:{ok:true}, clock:{ok:true},
    camera_actuator:{ok:false, reason:'no feedback', waived_for:waived},
    winch_actuator:{ok:false, reason:'no encoder', waived_for:waived}};
  assert.equal(startBlockReason(t, true, "mission"), "");
  assert.equal(startBlockReason(t, true, "mission_skip_corridor"), "");
  assert.match(startBlockReason(t, true, "delivery_here"), /Waiting for devices/);
  t.devices.winch_actuator = {ok:false, reason:'winch fault: stalled'};
  assert.match(startBlockReason(t, true, "mission_skip_corridor"), /stalled/);
  assert.equal(taskCommand("mission_skip_corridor", "").args.task, "mission_skip_corridor");
});

test("the organisers' six points: fence is their outline, zone corners kept apart", async () => {
  const { convexHull, organiserFence } = await import("../src/organiser.ts");
  // The venue survey, 30 Oct 2026: two points behind take-off, then the
  // delivery zone's corners (any order).
  const behind = [{ lat: 13.1703711, lon: 77.5331627 }, { lat: 13.1707773, lon: 77.5332852 }];
  const zone = [
    { lat: 13.1707636, lon: 77.5329365 }, { lat: 13.1705131, lon: 77.5330233 },
    { lat: 13.1705581, lon: 77.5328695 }, { lat: 13.1707149, lon: 77.5330967 },
  ];
  const fence = organiserFence(behind, zone);
  const key = (p) => `${p.lat},${p.lon}`;
  // The near zone corners lie inside the outline: back points and far corners.
  assert.deepEqual(new Set(fence.map(key)),
    new Set([...behind, zone[0], zone[2]].map(key)));
  // Counter-clockwise in (lon, lat).
  let area = 0;
  fence.forEach((p, i) => { const q = fence[(i + 1) % fence.length]; area += p.lon * q.lat - q.lon * p.lat; });
  assert.ok(area > 0);
  // No corners: the typed polygon goes as it is.
  assert.deepEqual(organiserFence(zone, []), zone);
  assert.equal(convexHull([behind[0], behind[0]]).length, 1);
});

test("organiser points: lat, lon parsing and which commands need a disarmed aircraft", async () => {
  const { parseLatLon } = await import("../src/organiser.ts");
  assert.deepEqual(parseLatLon("13.1705900, 77.5331760"), { lat: 13.17059, lon: 77.533176 });
  assert.equal(parseLatLon("13.17"), null);
  assert.equal(parseLatLon("91, 10"), null);
  assert.equal(parseLatLon("a, b"), null);
  const t = ready();
  t.gps = { lat: 13.17, lon: 77.53, sats: 14, fix: "3D" };
  assert.equal(reviewAllowed(t, true, "set_point", {}), true);
  assert.equal(reviewAllowed(t, true, "apply_organiser_points", {}), true);
  assert.equal(reviewAllowed(t, true, "record_point", {}), true);
  t.mission.armed = true;
  assert.equal(reviewAllowed(t, true, "set_point", {}), false);
  assert.equal(reviewAllowed(t, true, "apply_organiser_points", {}), false);
  assert.equal(reviewAllowed(t, true, "record_point", {}), true);   // moves nothing
  t.gps.fix = "NO";
  assert.equal(reviewAllowed(t, true, "record_point", {}), false);
});
