# AeroTHON Mission 2 master documentation

Maintained 14 October 2026. This is the operating manual and technical reference
for Team Rotor FPV's autonomous aircraft stack and revised GCS. Read `AGENTS.md`
before editing. These are the two maintained project Markdown documents;
historical reports and issues are archived locally rather than kept as competing
instructions. Commands containing `<...>` need measured replacement values.

## Contents

1. Current position and qualification
2. Architecture and source map
3. Mission algorithms and evidence
4. Configuration and organiser inputs
5. Pi bundle and installation
6. Wiring and calibration
7. Operation and recovery
8. Simulation and video
9. Hardware qualification
10. Maintenance and historical archive

## 1. Current position and qualification

Mission 1 is manually piloted. This repository primarily implements Mission 2:
read the start QR, align to an identified banner, traverse the outbound corridor,
search the delivery zone while avoiding restricted ground, deliver to the
matching QR pad, traverse the return corridor and land at home. ArduPilot
stabilises the aircraft; ROS 2 supplies mission decisions through MAVROS.

The next project step is Pi deployment and hardware integration. Hardware and
staged autonomous flights remain unqualified. Installation or simulation success
does not qualify the real camera, sensor orientation, actuator movement,
command delay, braking, payload retention or loaded/unloaded effort signal.

The latest pre-cleanup frozen candidate is V44, recorded in
`logs/reliability_reduced_scope_v44_source_20261013/provenance.json` with
987 controlled files and `accepted_source=false`. Frozen manifests identify
the exact source tested; Git alone does not identify older dirty-worktree runs.

Verified V44 results before consolidation:

- Reduced offline suite: 1,920 passed, eight skipped. The explicit strong-gust
  exclusions remain unresolved; this is not an unrestricted-suite pass.
- Calm rendered seed 20261003: laid-only, suspended-only and combined banner
  worlds each passed 22/22 checks with connected disarm. Their directories end
  in `_p2r11`. Graded flight times were 874.0, 832.0 and 819.1 s; closest
  obstacle clearances were 0.72, 0.71 and 0.77 m.
- Sixteen headless navigation cases passed across placements, banner heights,
  widths and calm/field conditions. Evidence is preserved in
  `logs/archived_phase2_20261014/p2v44_*_20261013`. Object-level navigation does not
  qualify rendered perception or motor delivery.
- The next laid-only rendered field run stayed in outbound banner alignment
  and was operator-aborted to permit consolidation. It landed and disarmed;
  `logs/phase2_rendered_clarified_h115_ground_s20261004_field_p2r12/summary.json`
  records `GRADE_FAIL`, `ABORTED_RTL`, and 398.9 s flight time. Its progress
  log's clock differs from the grading time. No 900 s violation is claimed.
  Queued repeats were stopped. This is not natural mission completion.

The original 96-flight reduced campaign and original five-course rendered gate
are separate from the clarified Phase 2 matrix. Completion of one does not
establish the other. Strong gusts/coupled delay remain unresolved. Laid-only
calm acceptance had just 26 s margin against the 900 s mission limit.

### Result of this consolidation

The cleanup removed the unused `std_msgs.Empty` binding, a duplicate package
dependency and the unused `echarts`/`echarts-for-react` frontend dependencies.
Missing launch dependencies were declared. Existing runtime Python changed
only in that unused import; its remaining AST is identical. Mission/planner
source and numeric FC parameters remain unchanged. Historical documentation
was archived before removing 104 superseded project Markdown files.

Fresh reduced offline checks passed 1920 tests with eight skips, plus syntax,
configuration and frontend build (`logs/offline_pi_cleanup_retry1_20261013.log`).
The runtime ZIP built all 11 local packages in an isolated workspace, imported
13 runtime modules from that extracted installation and expanded the CAD URDF
without simulator assets. The browser GCS and its offline tiles loaded.
Real camera/lidar drivers are absent on the development simulation host;
they still need destination installation. This does not qualify Pi hardware.

The requested narrow combined-banner field run, seed 20261004, completed
delivery, return and connected disarm but **failed acceptance, 21/22 checks**.
Its evidence is `logs/pi_cleanup_hard_field_both_s20261004_retry1_20261013`:

- Corridor minimum: **0.663645 m**, below the unchanged 0.70 m floor.
  The minimum occurred at native time 842.099 s by the first return obstacle;
  70 recorded aircraft samples were below the floor. The independent review
  is `.scratch/pi_consolidation_20261013/final_field_clearance_review.json`.
- Unexpected contacts: zero; independent evidence valid with seven channels
  and ground canary. Restricted-ground clearance: 1.631704 m.
- Flight: 886.1 s of the allowed 900 s. Native payload error: 0.11 m.
  Landing error from home: 0.65 m; connected disarm recorded.
- Motor-based delivery confirmation passed on attempt one after retraction.
  Supporting visual ground confirmation was absent; no dual-channel claim.
- Input isolation, source/runtime hashes and onboard timeline through disarm
  passed. The native overview exported at 1920x1080 H.264, 890.8 s duration,
  with 2670 actual captures and maximum capture gap 0.333 s.

The world video is `overview/world_overview.mp4` within that run; the clearance
event is around 13:03 in the exported timeline. It displays the actual FAIL.
Earlier interrupted attempts are retained separately and do not count as this
run. No algorithm correction or threshold relaxation was made during cleanup.
Field clearance requires a separate functional investigation before acceptance.
The Pi GPIO/encoder winch backend also remains to be implemented and measured
before operating the selected motor. The package is software preparation,
not permission for a full autonomous real-aircraft mission.

Work stopped at the user's request on 14 October 2026. The latest verified Pi
runtime bundle is `.scratch/pi_remote_runtime_20261014/runtime7.zip`, SHA256
`4b767bbfd837872152f4c2773af577fd165b16243e1cbe4d75809a999722a238`.
Its shared Pi/laptop runtime reached disarmed connection and preflight
observation, with no completed mission. Focused runtime checks passed 38 tests
and frontend checks passed 25. The latest broad offline command passed 1,955
Python tests with eight skips, then failed its frontend step. Later focused
fixes passed, but no complete final-source offline pass or new rendered
qualification is claimed. The stopped-project report is
`.scratch/stop_report_20261014/AEROTHON-status-report.html`; it records all
remaining obligations and the later flight-facing adapter/perception changes.
The user last supplied Pi address `192.168.0.100`. HTTP and SSH were unreachable
at the stop check, so current Pi process/armed state is unconfirmed. Last saved
telemetry was idle and disarmed. Documentation updated after the bundle freeze
is not represented as deployed evidence.

### 15 October 2026: organiser clarifications, final-source qualification

The AEROTHON_phase2 worktree was already removed and archived on 14 October;
its single extra commit (`d5ec31a`, rendered field conditions) is contained
in this working tree, so AEROTHON holds the latest code. The pi-web-gcs
worktree was an older GCS design, archived; the maintained GCS is here.

Changes made against the organiser clarifications (sections 3 and 4):
appearance-only QR identification with a module-grid signature and measured
0.94 bar; the start QR proceeds on its pattern when nothing decodes; the
interlock requires applied GCS arena dimensions; obstacle reach added as the
21st arena field; explicit vehicle kind (laptop simulation or real drone) in
connection profiles; QR target and match basis shown in the GCS; red-zone hex
labelled as such; delivery-search failures before lowering skip the drop and
still fly the return; the planner keeps a 0.10 m tracking reserve when the
space allows; MAVROS magnetometer encoding read as microtesla correctly.

Evidence, all calm conditions and arena dimensions applied through the GCS
preset path, source identity
`188aacd06fb893c697efe7a42026d9229d6114c119f9362a47e980686817a4c0` (1004
files, identical in both final runs):

- Offline: `logs/offline_s3_final_20261015.log` -- 1,971 passed, 18 skipped,
  five deferred strong-gust cases excluded (ledger
  `logs/offline_scope_s3_final_20261015.json`); native gateway 12 passed;
  syntax, shell, XML/YAML and frontend (25 tests, typecheck, build) passed.
- `logs/s3_final_calm_h115_both_appearance_s20261003`: combined banners,
  10 m corridor, decoded payloads ignored (pattern only). GRADE_PASS 22/22;
  corridor 0.748 m, restricted ground 2.111 m, payload 0.14 m, landing
  0.08 m from home, 848.0 s, contact-free, connected disarm.
- `logs/s3_final_calm_h115L5_both_payload_s20261003`: combined banners, 5 m
  corridor, payload decoding on. GRADE_PASS 22/22; corridor 0.774 m,
  restricted ground 2.099 m, payload 0.11 m, landing 0.15 m, 871.0 s.
- Diagnostic, earlier source: `logs/s3_calm_h115_both_appearance_s20261003`
  completed the mission by pattern alone but failed 21/22 on corridor
  clearance, 0.6984 m. It led to the planner reserve. Its readiness and QR
  sources were edited after its manifest was taken; it is not acceptance.

Later on 15 October four more changes were made and re-qualified: the planner
reserve above was already in; the search re-plans at once only for a NEW
obstruction on its active leg (a flickering red cell had re-planned run B's
sweep 86 times; the re-run re-planned once); the execution watchdog judges a
simulated vehicle's FCU freshness in vehicle time; recovery repeats its mode
request while the FCU stays GUIDED; and the Pi GPIO/encoder winch backend was
added. On that final source: `logs/offline_s3_final2_20261015.log` -- 1,984
passed, 18 skipped, five deferred strong-gust cases excluded, native 12
passed, frontend passed -- and
`logs/s3_final2_calm_h115_both_appearance_s20261003`: GRADE_PASS 22/22,
corridor 0.770 m, restricted ground 2.144 m, payload 0.15 m, landing 0.16 m,
873.0 s, contact-free, connected disarm. The Pi-role bundle is
`logs/pi-runtime-rulebook-20261015c.zip` (256 files, SHA256
`ac43d1b5100220b3a37786e2cd593efcab016990a09a21ebef8bd9c4aedc85a4`).

GCS integration, laptop-simulation mode, Pi role (bundle built in a fresh
workspace on this laptop because the Pi was unreachable), browser GCS as the
only operator interface, receipts `logs/pi_role_gcs_mission_20261015*/`:
profile save/Connect, arena APPLIED by the mission, hex colours, zone and fence
through reviewed commands, all 15 readiness items Ready, GUIDED and reviewed
Start each worked. Attempt 1 aborted on the wall-clock FCU watchdog and its
single RTL request was lost (both fixed). Attempt 2 flew the whole outbound
lap and searched until stopped from the GCS (RTL, landed 0.08 m from start).
Attempt 3 flew outbound, matched pad B, lowered and confirmed delivery by
motor effort (0.25 m image offset), then the 1 s laptop-sim clock watchdog
handed over to FCU recovery (allowance now 3 s). Attempt 4 was stopped during
the search by a command from a separately started deploy session sharing the
host. No Pi-role run has yet flown the return corridor; the rendered
acceptance runs above fly the same algorithms through it.

Flight time is 848-873 s of 900 s in these calm worlds; the search sweep
is the largest share. Strong gusts, delayed control, the original five-gate
campaign and all physical qualification remain open, and the Pi (last
addresses .100/.101) was unreachable on 15 October, so the new bundle is not
deployed.

## 2. Architecture and source map

Native deployment targets Ubuntu 24.04 arm64 and ROS 2 Jazzy. Current launch
defaults describe the CAD airframe, C270 camera geometry and LD06 interface.
Verify the physical build rather than copying older Brio/C1/Iris proposals.

```text
camera -> QR/banner/red-ground/payload perception -> mission tree
lidar -> mount correction -> local avoidance -> MAVROS setpoints
FCU -> MAVROS pose/velocity/motor telemetry -> mission and avoidance
mission -> camera_ctrl / winch_ctrl -> MAVROS actuator commands
mission + FCU + perception -> readiness / WebSocket aggregator
operator browser -> aggregator -> guarded operator commands
combined camera overlay -> web_video_server -> browser
```

Native Gazebo truth, collisions, attachment state, world layout and evaluator
cameras belong to evaluation. They do not enter flight decisions. Simulator
contact release physically detaches the payload; it does not decide lowering,
retry or delivery success.

One process owns each physical link. In the router topology,
`scripts/mav_router.py` owns the FC telemetry serial device; MAVROS consumes
local UDP and Mission Planner receives a separate stream. ROS DDS stays local
with `ROS_LOCALHOST_ONLY=1`. Operator traffic uses WebSocket/HTTP/MJPEG and
optional MAVLink. The current GCS is command-capable, not receive-only.
RC pilot authority and FC failsafes remain independent of ROS.

Source map:

- `src/aerothon_mission/mission_bringup`: launch, venue/FC settings, stream
  keeper and corrected scan mounting.
- `src/aerothon_mission/mission_bt`: tree, MAVROS commander, physical braking,
  lane routing, arena dimensions and delivery observer.
- `src/aerothon_mission/uav_description`: sensor frames and vehicle URDF.
- `src/aerothon_avoidance/avoidance`: local planner, compiled-path helper,
  velocity controller, buffered scans, capture inbox and independent clock.
- `src/aerothon_perception`: QR, banner, red-ground, payload, overlay and
  camera control. Payload executable belongs to `perception_redzone`.
- `src/aerothon_payload/winch_ctrl`: winch intent and estimated travel.
- `src/aerothon_gcs/gcs_aggregator`: readiness, telemetry, calibration and
  command dispatch. `tauri_app` contains the revised React/Vite browser UI
  and optional desktop wrapper.
- `sim/`, `src/aerothon_sim`, developer `scripts/`: physics, fixtures,
  independent grading and recording. These stay on the development host.

Key interfaces include `/mission/arena_dimensions`, `/mission/banner_colours`,
`/mission/delivery_zone`, `/mission_ready`, `/mavros/local_position/pose`,
`/mavros/local_position/velocity_local`, `/scan_raw`, `/scan`, `/image_raw`,
`/camera/pose_state`, `/percep/*`, `/winch/cmd`, `/winch/status` and
`/mission/delivery_observation`. Inspect the live graph with `ros2 node info`
and `ros2 topic info` for exact publishers/subscribers.

Default services are WebSocket 8765, MJPEG 8080 and static GCS HTTP 8899.
Simulation MAVLink ports can be shifted independently.

## 3. Mission algorithms and evidence

The behaviour tree waits for explicit START, validates the search area
(the judges' geofence, or supplied delivery-zone corners) and
uploads/read-back-verifies the FC inclusion fence before arming in GUIDED. Normal stages are:

1. Take off and settle; look down; find/centre the start QR. A payload
   confirmed over three frames becomes the target. When nothing decodes for
   8 s while perception holds the marker as a QR module grid, the target is
   the marker's pattern alone (`APPEARANCE_ONLY`); see QR identification.
2. Identify the outbound banner using supplied colour and white-frame
   structure. Lettering is an optional confirming path. Suspended, ground
   and combined banners use different views and ranging. Combined gates
   try hung alignment first, then a ground glance/pass when identified.
3. Align, descend/duck under, brake and cross the gate; traverse the
   outbound corridor below its walls.
4. Enter the organiser delivery boundary and search from its south-west
   corner. Camera geometry, marker size and capture rates determine sweep
   coverage. Confirmed red-ground observations become local exclusions.
5. Descend to read the candidate pad, confirm its target identity and centre.
6. Lower, infer unloading, test release, retract and assess fresh calibrated
   FCU motor effort for delivery confirmation.
7. Climb, transit to the return gate, identify/align its banner, traverse the
   obstructed return corridor and land/disarm at home.

Local avoidance uses aircraft-relative scans, timestamped pose and fresh FCU
velocity. Braking and certification include response/command age and compute
time. Unknown or insufficiently clear routes fail closed. The actual controller
imports `FastConnectedPlanner` from `fast_connected_planner_candidate.py`;
that filename does not mean it is disposable. Bounded continuous certificates,
physical gate/height holds and tight-origin/stub-waypoint rules are qualified
functional changes and must be preserved during cleanup.

### QR identification

The organisers have not confirmed that the codes encode anything and require
matching by visual appearance. `qr_appearance.py` rectifies each located
marker, reads it as a 21-41 module grid turned so the corner without a
finder pattern is bottom-right, and compares data modules only; finder,
timing, format and alignment modules are identical across codes and are
excluded. The start marker seen while no target exists is the reference;
each START publishes an empty target so every flight captures its own.

Measured on rendered OpenCV codes under perspective, rotation, blur, gain and
noise (`logs/qr_appearance_study_20261014`), the same code scored 0.95-1.00
and codes differing by one character ("A"/"D", sharing padding) at most
0.894. The match bar is 0.94; the coarse fallback for non-standard patterns
needs 0.93 and never compares with a module grid. A decoded payload that
contradicts the target vetoes a visual match, and a payload that only shares
identifiers with the start code (start "ZONE 2 PAD 1", pad "2") does not
outvote two module grids that differ. Identical payloads still match.
`AEROTHON_QR_IGNORE_PAYLOADS=1` (launch) discards decoded payloads to fly the
no-data case in simulation.

Route choice keeps a tracking reserve. The hard centre-to-surface limit is
0.70 m, and routes were planned only 0.025 m beyond it; following them cost a
few centimetres, and return-corridor minimums of 0.664 m (field) and
0.698 m (calm, 15 October) fell below the floor. `FastConnectedPlanner` now
prefers a route keeping 0.80 m (limit + 0.10 m) and the straight route only
when it keeps that much; when the gap is too narrow it falls back to the
former 0.725 m route or clear straight line. Certificates, braking and the
hard limit are unchanged.

Independent grades retain 0.70 m corridor clearance, 1.50 m restricted-ground
clearance and 900 s full-mission time. Offline/nav/rendered/physical evidence
have different meanings and cannot substitute for one another.

### Payload delivery

Mean squared normalised motor PWM is the primary hover-effort proxy. It is
neither measured current nor thrust. Separate loaded/unloaded stable-hover
calibration requires sufficient samples and disjoint effort bands. Profiles
from the simulator do not qualify the aircraft. IMU, tilt and velocity reject
unstable intervals; battery current is not an individual motor measurement.

Camera apparent-size range supports the observer but is not a contact sensor.
Sustained unloading starts a short retraction test. Returning load triggers
another lowering attempt. The current code lifts the empty claw before waiting
to avoid pad drag. Confirmation requires sustained unloaded evidence after
full estimated stow. Travel and stow currently remain estimates.

If the sweep ends without a match, the matched pad stands on confirmed red
ground within the clearance, or centring times out -- all before the winch
moves -- the mission records `delivery_skipped`, does not lower, and flies the
normal return lap and landing (result `DELIVERY_SKIPPED`). The return,
landing and time are 40 rulebook marks that do not depend on the payload; the
former behaviour failed the mission into an FC recovery that never flies the
corridor. Winch-stage failures still fail the mission, as a payload may hang.

There are three attempts and a 300 s observation budget. Exhaustion retracts
and continues with `DELIVERY_UNCONFIRMED`; recovery has a separate 45 s limit.
A fault/incomplete recovery fails the stage. Preserve distinctions between
`payout_estimate_m`, `payout_basis`, `release_requested`, `touchdown_inferred`,
`detachment_inferred` and `delivery_confirmed`.

## 4. Configuration and organiser inputs

`mission2.launch.py` selects devices/backends and `params_file`.
`mission_bringup/config/venue.yaml` stores venue/airframe parameters. ROS float
parameters need decimal values, such as `4.0`. Camera HFOV is radians and must
match the fitted lens.

On the ground, enter organiser dimensions and colours in the GCS arena panel,
save/load a preset, APPLY and wait for aircraft applied confirmation. The
readiness interlock item **Arena dimensions** blocks every flight start until
the mission reports the operator's values applied; it shows the applied QR
side and corridor length/height. Without it the aircraft would fly launch
defaults (a 2.2 m QR instead of the organisers' 1 m). Simulator scripts that
hand the mission its arena as launch values, with no GCS preset, set
`AEROTHON_REQUIRE_ARENA_DIMENSIONS=0` and the item reads WAIVED. The 21
fields cover corridor, hall, banner, QR, red zone, payload and the exit-
corridor obstacle reach (fraction of corridor width, organisers' "about
half"). Fields marked "rec." are recorded for the operator only. Input
units are converted to the aircraft schema; the tree is rebuilt from accepted
dimensions. Fields not used by an algorithm are labelled. The simulated
operator uses this same WebSocket path, not world-truth injection.

The browser GCS uses the same plain workspace for Flight operations and
Testing. Camera, SLAM, Map and Graphs share the persistent status strip,
task controls, readiness, event log and connection settings. Tests select
`mission`, `slam`, `qr`, `banner`, `avoidance_manual`, `avoidance_route`,
`mechanism`, `delivery_here` or `delivery_gps`. The supervisor uses the current
production tree and components. QR and SLAM observation do not arm. Mechanism
bench tests require disarm and measured actuator capability. Flight tests
use one reviewed Start, then production return/land on completion or Stop.
Transmitter takeover releases command ownership without a competing mode request.

Open `http://<pi-address>:8899/`. Browser API, WebSocket `/ws`, video and map
requests use the same origin. Each connection profile names its **Vehicle**:
*Laptop simulation* (the Pi runs the flight code and GCS and connects over the
intranet to Gazebo and SITL on the laptop: FCU TCP port plus sensor gateway)
or *Real drone* (FC UART or a network telemetry link, Pi camera and lidar, no
gateway, secured props-off review required before Connect). The header shows
the active profile and vehicle kind. Flight operations and Testing work with
either vehicle. Connections saves vehicle profiles on the Pi:
FCU TCP/UDP/UART, hostname, ports, system/component identity, remote sensor
gateway, local devices, calibration and RC mappings. Save only with runtime
stopped and aircraft disarmed. Connect prepares sensors and the supervisor;
it does not arm, start a mission or move the camera. A profile with SLAM enabled
starts production mapping; the GCS displays its frame, origin and timestamp.
Camera view tabs do not move the camera; explicit camera tilt is reviewed.
Before flight, enter green, orange and red as `#RRGGBB` in Organiser inputs,
then review Apply banner colours while disarmed. All three are required.
The applied values appear in telemetry. Banner and restricted-zone masks,
including clipped-zone evidence, derive their hue ranges from these values;
missing values do not use fixed fallback bands or establish a clear zone.

For laptop simulation, run `bash scripts/launch_laptop_sim.sh` in the built
Ubuntu/Jazzy workspace. It reuses the current vehicle/world launcher with
`mission_stack:=false`: Gazebo, SITL, device bridges and gateway run on the
laptop; production perception, avoidance and execution run only on the Pi.
The gateway needs `pymavlink` in a Python environment compatible with the
system ROS/cv_bridge NumPy. TCP port 5762 carries FCU commands/telemetry; HTTP
port 8090 carries the manifest and separate camera/sensor WebSockets. Configure
the laptop hostname/IP and `http://<laptop>:8090` in the Pi profile. With WSL
NAT, expose those TCP ports on the laptop intranet address to WSL; configure
the profile with the exposed address. DDS stays local (Pi domain 42, laptop 43).
On Windows this machine reserves TCP 8075–8174, including 8090. Use the
configurable sensor port 19090 here, and set the gateway URL accordingly.
`scripts/laptop_gateway_relay.py --bind <laptop-intranet-IP> --target <WSL-IP>
--sensor-port 19090` exposes the two explicit services without exposing DDS.
The gateway receives actual SITL actuator PWM and measured model joints;
world layout, grading, contacts and payload attachment state stay on the laptop.
Connection check reports identity, camera/calibration, lidar, clock and each
actuator independently. Wrong identities, stale captures, paused/backward
clock and unsupported actuators block affected executions. Gateway restarts
(a new session) require explicit disconnect/reconnect. A stream the network
drops on the same session is reopened by the Pi after 1 s
(`remote_devices.STREAM_RETRY_S`, counted in `/devices/status`
`identity.streams_reopened`); the gap shows as stale receipts and, past 3 s,
a clock fault, never as fresh data. A manifest poll may go unanswered for up
to 10 s before the link faults, and identity reads not-ok once the last answer
is over 1 s old. The gateway allows 5 s per sensor send
(`gateway.SEND_TIMEOUT_S`); its former 0.5 s limit closed `/sensors` on a
congested LAN to the real Pi, freezing the vehicle clock until a manual
reconnect (`sim/test_remote_device_link.py` reproduces that failure against
the old driver). Watchdogs use steady time.

Laptop-simulation mode was exercised end to end on 15 October with the bundle
built in a fresh workspace in the Pi's role (domain 42) and Gazebo/SITL/gateway
on the laptop side (domain 43); the operator flow was the browser GCS only. Two
defects found and fixed: the execution watchdog judged FCU freshness on wall
time, so SITL's 1 Hz heartbeat at a third real time tripped "FCU telemetry
lost" (a simulated vehicle is now judged in vehicle time; its clock's own
liveness stays a steady-time device-link check); and the recovery mode request
was sent once, so a request lost in the same gap left the aircraft hovering in
GUIDED (now repeated each second while the FCU still reports GUIDED and armed,
never over a pilot or FCU mode). In this mode the whole Pi stack, Gazebo and
the camera relay share one laptop: the red-ground detector delivered about
5 Hz of simulated time and the search pacing, which waits for both detectors,
swept far slower than the rendered acceptance runs. That is a host-throughput
limit of the test arrangement, not a reason to relax the pacing interlock.

Arena fields use the production schema and remain editable offline as a draft.
Aircraft application requires live disarm; command receipt and applied
confirmation differ. Cached satellite coverage does not invent an aircraft GPS.

Graphs retain ten minutes at up to five samples per second, with gaps for
stale/missing sources, selectable traces, pause and CSV export. Vibration
comes from MAVROS VIBRATION, and magnetic field from `/mavros/imu/mag` in
microtesla. MAVROS fills that message from ArduPilot RAW_IMU/SCALED_IMU
milligauss multiplied by 1000 rather than 1e-7, which produced the recorded
5.789e11 uT; the aggregator reads any value above 0.01 T as that encoding
(uT = value x 1e-4) and reports `magnetic_units_basis`. Magnetic deviation uses an explicit disarmed reference; it is an
indicator, not a calibrated interference percentage. Camera/lidar receipt
rates and ROS capture ages are separate. Winch travel remains an estimate
until measured encoder feedback exists.

Commands use durable IDs stored before dispatch in the Pi SQLite receipt
ledger. Reconnects and duplicate requests do not repeat arming or release.
Submitted, Accepted, Running, Completed, Failed and Outcome unknown are distinct.
An Accepted receipt is not proof of motion, release, delivery or disarm. After
an unknown outcome, inspect fresh evidence before another start. Recovery
remains available when readiness fails. One supervisor owns movement; new
starts cannot replace active executions. Hardware camera/winch motion and
physical delivery remain unqualified; the GPIO/encoder winch backend exists in
software but is unmeasured and bench-unverified.

**The judges' geofence is the one organiser polygon.** They give six
coordinates. Paste them into Organiser inputs, one `latitude, longitude` per
line: the GCS counts them, draws the draft dashed on the Map tab, and after
Apply geofence draws the applied polygon filled. No delivery-zone corners are
entered. The rulebook says "Delivery zone geo-fence coordinates will be
provided"; the team expected a fence round the whole flying area. Take-off
decides which (`delivery_zone.judges_polygon_role`), on the aircraft and in
readiness alike:

- **Take-off inside the points: arena fence.** The polygon is the FC inclusion
  fence (take-off at least 2 m inside). Once the outbound corridor's exit is
  known in flight, the mission takes the part of the fence at least 1 m beyond
  the exit (across the squared gate heading) as the field, searches its
  bounding box inset 1 m and trims every sweep lane to stay 1 m inside it
  (`clip_beyond`, `chord_inside`). "Search area" reads "fenced field beyond the
  corridor".
- **Take-off outside the points: delivery zone.** The polygon is the search
  area, known before take-off, with lanes trimmed 1 m inside it. The FC
  inclusion fence is derived: the hull of the zone and a 5 m square round
  take-off, grown 10 m outward (`safety_fence`), which holds both corridors.
  "Arena geofence" reads "derived round the delivery zone and take-off" and
  "Search area" reads "judges' points (delivery zone)".

Supplied four-corner delivery zones (the simulator's default) still take
precedence when present; `AEROTHON_FENCE_ONLY=1` makes the simulator publish
the polygon alone (`sim/fly_headless.py --fence-only=X,Y;...` in headless
runs). An arena fence much larger than the real delivery zone means a longer
sweep: the calm sweep runs at about 0.65 m/s, limited by stopping 1.5 m short
of red ground first seen 2.55 m ahead, and that limit is kept.

**Search deadline.** The sweep stops when it is still searching
`mission_limit_s - return_reserve_s + search_deadline_extension_s`
(900 - 300 + 300 s by default since 15 October; see "Arena reading" below)
after the FCU armed; the
delivery is then skipped and the return lap flown (`search_overdue`,
`SkipDeliveryAndReturn`). The reserve covers the 275 s from the drop's start to
landing in the calm rendered acceptance. A match before the deadline is still
delivered. The rulebook's 15-minute window holds return, landing and time
marks (40) against payload delivery (15).

The reserve is a trade-off, not a guarantee. From the far field, the rendered
return without a drop took 287 s from the deadline to landing (banner
alignment 107 s of it). A match just before the deadline adds about 70 s of
centring and drop, which could reach about 957 s. A 370 s reserve would rule
that out, but its 530 s deadline would have skipped the passing delivery-zone
run, which matched about 587 s after take-off and landed delivered at 873 s.
The 300 s default keeps that delivery and is the value validated on the skip
path (887 s). The rendered camera's 3.5 Hz makes alignment slower than the
aircraft's camera should. Tune `mission_limit_s` and `return_reserve_s` from
timed field rehearsals; they are launch parameters.

Calm headless comparison on `clarified_h115_both`, seed 20261003, arena through
the GCS preset (`logs/headless_*_calm_h115_20261015/`): supplied corners, the
six points as the delivery zone and the six points as an L-shaped arena fence
all found and centred on the target. Drop at 494 s, 509 s and 644-690 s
simulated respectively; the arena reading swept 7 lanes against 5. The headless
fixture has no motor-effort model, so each delivery then failed closed
(calibration or loaded-hover baseline unavailable) and no headless return lap
was flown. These are object-level runs, not acceptance; the deadline was added
after them.

Calm rendered acceptance with only the six judges' points as an arena fence
(`logs/s3_fence6_calm_h115_both_appearance_s20261003`, QR by appearance, arena
through the GCS preset): the mission derived the field beyond the corridor
exit, swept 7 lanes 3 m inside the fence, and at 600 s after arming the search
deadline skipped the delivery (target on the far lanes) and flew the return.
Result DELIVERY_SKIPPED, 18/21 checks: flight 887 s (within 900 s), inside the
geofence, both corridors flown through at 0.778 m clearance, red clearance
2.14 m, no contacts, precise landing 0.15 m from take-off, disarmed. The three
payload checks failed because nothing was lowered. The return from the far
field took about 287 s of the 300 s reserve. This is not an accepted mission:
an arena-sized polygon costs the delivery in this layout. With the points as
the delivery zone the sweep matches supplied corners (headless above).

The same calm rendered world with the six points as the delivery zone
(take-off outside them; `logs/s3_zone6_calm_h115_both_appearance_s20261003`)
passed 22/22: the mission derived an 11-vertex safety fence round the zone and
take-off, swept the zone's 5 lanes, delivered 0.15 m from the pad, flight
880.1 s, corridor clearance 0.751 m, red clearance 2.07 m, landed 0.12 m from
take-off. The user later confirmed the judges' points enclose the whole arena,
so the arena reading is the competition case.

**Arena reading, tuned for the competition case (15 October).** Three changes
apply only when the search field is the arena fence beyond the corridor
(`mav.arena_search`): lanes 20% overlapped instead of 30%
(`arena_lane_overlap`, 7.3 m spacing at 10 m, a 1 m pad still wholly in frame
with about 0.4 m to spare: 6 lanes instead of 7 on the test field); the first
plan flies the whole sweep reversed when its far end is nearer the aircraft,
kept through mid-sweep re-plans (`LawnmowerSearch._descending`); and, by the
team's explicit choice, the search deadline is extended 300 s
(`search_deadline_extension_s`, to 900 s after arming) so a far-side target is
still delivered, accepting a flight past 900 s. `mission_limit_s` stays 900 and
the 900 s acceptance check is unchanged. A failed mission now keeps asking the
FC to land or RTL every 2 s while the last FCU report says armed in GUIDED
(`ensure_failed_recovery`): a GPU-rendered run (`..._ext300_gpu_...`, failed at
the gate on stale lidar) had hovered after FAILED until an operator landed it.
GPU sensor rendering on this laptop's Intel UHD is slower overall (about 0.18x
against 0.27x real time) and starves the lidar, so rendered runs stay on the CPU.

Calm rendered arena runs, six points only (`clarified_h115_both`, QR by
appearance, arena through the GCS preset): with 20% overlap alone, DELIVERY_SKIPPED
18/21 at 868 s, the far-lane target about 40 s short at the deadline
(`..._arena6_overlap20_...`); with the 300 s extension, COMPLETED, delivered
0.14 m, 21/22, failing only "flight within 900 s" at 914 s
(`..._arena6_ext300_...`); with the near-end start as well, COMPLETED 22/22 at
490 s, delivered 0.21 m, corridor 0.76 m, red 3.38 m, landed 0.12 m
(`logs/s3_arena6_nearstart_calm_h115_both_appearance_s20261003`). In that world
the target lies on the side nearer the corridor exit, so the near-end start
finds it early; a target on the far side of a large arena is the 914 s case.

The arena inclusion fence bounds the flight; the field derived from it (or
supplied corners) bounds search. Confirmed red observations become local exclusions, not additions to
the FC inclusion fence. Camera footprint over red differs from aircraft entry.

Preserve aircraft state in `~/.aerothon/dimension_presets.json`,
`~/.aerothon/lidar_mount.json` and the measured profile selected by
`AEROTHON_DELIVERY_CALIBRATION`. Defaults and example device/IP names are not
measurements. Record real configurations separately from source installation.

## 5. Pi bundle and installation

On the development host, build the revised GCS and create a new bundle:

```bash
cd src/aerothon_gcs/tauri_app
npm ci
npm run build
cd ../../..
python3 scripts/package_pi_runtime.py --out logs/pi-runtime.zip
```

The ZIP contains 11 local flight/GCS ROS packages, selected operating scripts,
built `gcs/` assets with offline satellite tiles, these two guides and a SHA256
`runtime_manifest.json`. It excludes simulator packages/models, tests, evidence,
developer tools, CAD, Node/Rust dependencies, build/install outputs and caches.
It refuses an existing ZIP. Build ROS output on the destination architecture.
External drivers and OS dependencies are not application source.

Identify Pi OS/version/architecture first. This native route requires Ubuntu
24.04 arm64 and the official Jazzy APT repository. The flight dependency set is:

```bash
sudo apt update
sudo apt install -y ros-jazzy-ros-base ros-dev-tools \
  ros-jazzy-mavros ros-jazzy-mavros-extras ros-jazzy-cv-bridge \
  ros-jazzy-web-video-server ros-jazzy-usb-cam ros-jazzy-xacro \
  ros-jazzy-robot-state-publisher ros-jazzy-py-trees \
  python3-colcon-common-extensions python3-opencv python3-numpy \
  python3-scipy python3-serial python3-websockets python3-pyzbar \
  tesseract-ocr libzbar0
```

Install MAVROS GeographicLib datasets with its packaged installer and verify
geoid data. Add reviewed upstream `ldlidar_stl_ros2` source to the workspace
and record its revision; that external driver is not in the application ZIP.
Match the driver to the actual fitted lidar.

The tested development environment uses websockets 10.4; its server startup
API differs from recent major versions. Verify imports/API before deployment.
Source Jazzy to expose py_trees. Keep NumPy compatible with distro `cv_bridge`;
do not let an unrelated Python environment override the ROS ABI.

Extract into a fresh `~/aerothon_ws`, verify the manifest, then:

```bash
cd ~/aerothon_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
bash scripts/check_pi_runtime.sh
bash scripts/serve_gcs.sh
```

The prerequisite check is read-only. It does not arm or establish hardware
qualification. Static serving is separate from ROS launch. Open
`http://<pi-ip>:8899/` on the operator laptop and connect to
`ws://<pi-ip>:8765`; loopback in the UI is for local development. Video uses
the chosen host and port 8080. No npm/Node/Tauri compiler is needed on the Pi.
Use the isolated operator network; this is not an authenticated Internet
service. The bundle does not install a boot/autostart service.

### Debian 13 Pi deployment

The destination is `pi5@192.168.0.101`, Debian 13 arm64 on a Pi 5 with 8 GB RAM.
Use the Ubuntu 24.04/Jazzy container route on this OS. Installing Ubuntu ROS
APT packages directly into Debian would mix distributions. The pinned official
ROS base image and dependency recipe are in `scripts/pi_runtime/Dockerfile.dependencies`.
Build that as `aerothon-dependencies:20261014`, then build
`scripts/pi_runtime/Dockerfile` as `aerothon-runtime:20261014`. The final stage
uses the completed dependency image directly and clears installation proxy settings.
Build dependencies inside that environment; Node, Rust, Gazebo and SITL stay
off the Pi. The external LD06 driver is pinned to upstream revision
`bf668a89baf722a787dadc442860dcbf33a82f5a`, with its own inventory.
Apply `scripts/pi_runtime/ldlidar-pthread.patch` in the driver directory before
compiling. It enables the upstream's commented Linux pthread include, required
by the destination compiler. It changes no mission or scan-processing decisions.

Application source and built GCS belong in `/home/pi5/aerothon_ws`.
Destination launchers/configuration belong in `/home/pi5/aerothon-deploy`.
`runtime.env` records UART, device names and sensor defaults. Change those
values only to measured configuration. The real delivery profile belongs in
`/home/pi5/.aerothon/`; it is not supplied by a simulation run. Containers run
as UID 1000 with host networking, local DDS domain 42 and explicit camera/lidar
device access. The host Python router alone owns the FC UART.

Install the destination services after building the ARM64 workspace/image:

```bash
sudo bash /home/pi5/aerothon_ws/scripts/pi_runtime/install_services.sh
sudo bash /home/pi5/aerothon-deploy/run_container.sh check
```

`aerothon-gcs.service` runs the Pi web host inside the Jazzy container.
It starts at boot with no vehicle execution. `aerothon-router.service` watches
the explicitly selected hardware profile and is the single UART owner.
Network profiles use MAVROS directly through their configured TCP/UDP endpoint;
they do not open the physical UART. The former console service is disabled,
and direct mission-service launch refuses to create a second controller.

The web process is supervised inside a persistent container. A web-process
restart can adopt its existing ROS child by boot/PID identity. Service shutdown
first requests safe runtime disconnect; it refuses termination of a controlled
runtime without live disarm. The Docker attach process uses `--sig-proxy=false`
so a refused stop does not forward a kill to the flight container. Power loss
and FCU failsafe remain separate hardware concerns.

Open `http://192.168.0.101:8899/`, select Connections, save a profile, Connect
vehicle and run Connection check. For hardware, use the measured TELEM3
`/dev/ttyAMA0` at 115200 and review secured props-off wiring first. At the last
inspection this device was absent. `/dev/serial0` is the debug/login UART.
For laptop simulation, use its gateway endpoints instead. Supply organiser
arena dimensions, the judges' geofence and banner colours through the GCS,
inspect readiness, then Review start and Confirm Start.

At inspection, the old standalone GCS, disposable SITL, MAVProxy and redundant
native MAVLink Router installation were replaced. Thonny was removed. Their
source/configuration and recorded simulator state were archived locally before
removal, excluding reproducible Python dependencies. The local recovery archive
is `.scratch/pi_deploy_20261014/previous_pi_installation.tar.gz`, SHA256
`0bc97164f00c615d445bb6fb91ae026d3dcfb8503fadb8f2e3034d1cd32731af`.
Installation used a temporary loopback-only SSH proxy because the Pi's direct
Internet/DNS path stalled. Running the installed stack/GCS does not require
that tunnel. Deployment receipts belong under `.scratch/pi_deploy_20261014/`.

## 6. Wiring and calibration

### FC communication and camera servo

The hardware file proposes TELEM2, MAVLink 2 and 921600 baud. Confirm connector
pinout, electrical levels, ground, permissions and the actual device first.
The inspected Pi's prior measured setup used TELEM3, `/dev/ttyAMA0`, GPIO14 TX
and GPIO15 RX at 115200 baud. That destination setting takes precedence over
the proposal until a deliberate FC link change is measured. `/dev/serial0`
currently names the Pi debug UART `/dev/ttyAMA10` and its login console.
In the documented topology the router owns the serial device:

```bash
python3 scripts/mav_router.py --fcu-serial /dev/ttyAMA0 --fcu-baud 921600 \
  --mavros-port 14555 --gcs-port 14550 \
  --gcs-host <laptop-ip> --gcs-out-port 14550
```

MAVROS uses `udp://127.0.0.1:14555@127.0.0.1:14556`. Direct serial MAVROS
requires the router to release that device. Never share the physical UART.

The user identified the FC as CUAV X7+ and confirmed ArduPilot **SERVO9** for
camera tilt. Confirm its physical output connector; this does not mean AUX9.
The file assigns `SERVO9_FUNCTION 7`, `MNT1_TYPE 1`, MAVLink targeting and
-90 to +30 degree pitch limits. Measure PWM endpoints, direction, supply,
angles and travel before use.

Camera poses are FORWARD 0, NADIR -90, ALIGN -45, BANNER -20 and GROUND -35
degrees. Fresh mount attitude is preferred. `readback=timed` assumes the
requested angle after the delay; it proves neither movement nor FC command
acceptance. Observe each pose and measure worst-move settlement.

### N20 motor and encoder

Selected motor: [N20 12 V 60 RPM with encoder](https://robu.in/product/n20-12v-60rpm-micro-metal-gear-motor-with-encoder/).
User-supplied motor specifications are 12 V, 60 RPM no-load, 40 RPM rated,
1 A stall current and 298:1 gearbox. The user chose a BTS7960 43 A H-bridge.
These specifications are not measured winch performance; a 43 A driver rating
does not provide suitable small-motor stall protection by itself.
User-supplied wire functions: red/white motor terminals, black encoder VCC
3.3–5 V, blue encoder ground, yellow/green encoder feedback. Confirm output
voltage, signal type/resolution and motor stall current from specifications
and measurements. Encoder supply voltage alone does not establish output
compatibility or identify which signal leads in each direction.

Recommended integration is Pi control through a suitable H-bridge with encoder
acquisition on compatible Pi inputs; the camera servo remains on the FC.
Motor red/white connect to the driver, never GPIO or a servo signal output.
Use a regulated/current-protected 12 V motor supply, not a fully charged 4S
pack directly. Pi inputs need
3.3 V-compatible signals; use a suitable interface where outputs differ.
See [Raspberry Pi GPIO guidance](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html).

An FC-driven compatible winch controller is an alternative. `winch_ctrl`
has two hardware backends: `mavlink` sends `MAV_CMD_DO_WINCH`; `gpio`
(`winch_ctrl/gpio_winch.py`, 15 October) drives the BTS7960 from the Pi
through `lgpio` (Pi 5 compatible) and measures travel from the N20 encoder in
quadrature. It writes the inactive PWM to zero before driving the other side,
drops both enables on stop, stops and faults when driven with no counts for
0.6 s or counting against the drive, and treats a stall within 0.15 m of
stow as the hook at its stop (the stow reference, count re-zeroed). Payout is
then measured line movement (`payout_basis: measured N20 encoder travel`).
It refuses to start, faulting the winch closed, until the venue parameters
`encoder_counts_per_output_rev` and `spool_radius_m` hold measured values;
`encoder_lower_sign` and `drive_duty_pct` follow the bench. Select it per
real-drone profile (GCS Connections, Winch) and set
`AEROTHON_WINCH_BACKEND=gpio` in `runtime.env` so the container is given the
GPIO devices; the image needs `python3-lgpio` (in the dependency recipe). It is
software tested against a simulated bridge and encoder only, not on the bench.
Existing SERVO10/PWM configuration is
a proposal, not confirmed N20 support. The wiring record
`mission_bringup/config/hardware_wiring.yaml` is inert and explicitly marks
  assigned driver/GPIO wiring and unmeasured encoder values. It does not enable
  a connection.

Assigned wiring, also recorded in the YAML:

- BTS RPWM: BCM18, physical pin 12; LPWM: BCM19, physical pin 35.
- BTS R_EN: BCM22, physical pin 15; L_EN: BCM23, physical pin 16.
- Encoder yellow: BCM17, physical pin 11; green: BCM27, physical pin 13.
- Encoder black: 3.3 V, physical pin 1; blue/common signal ground: physical
  pin 6. Verify output voltage remains within 3.3 V.
- BTS logic VCC: reviewed regulated 5 V rail, physical pin 2 if supplied by
  that rail; GND to the common reference. Motor B+/B- use the separate 12 V
  supply. Red/white motor wires use M+/M-.
- Leave R_IS/L_IS unconnected. No analog current acquisition is implemented.

The [BTS7960 module guide](https://www.handsontec.com/dataspecs/module/BTS7960%20Motor%20Driver.pdf)
documents RPWM/LPWM, active-high enables, 5 V logic supply and 3.3–5 V control
inputs. Check the actual module against this interface; an input buffer that
requires 5 V highs needs a suitable 3.3-to-5 V interface. Verify direction;
motor leads or encoder phase order can reverse it. Future control must keep
inactive direction PWM zero, disable enables on stop/fault, establish real
stow and detect missing/stalled encoder feedback. Verify the Pi 5 PWM API;
selecting pins does not implement PWM. Encoder counts/shaft turn remain unknown.

At the user-rated 40 RPM, line speed depends on spool radius:
`speed_mps = 2 * pi * effective_radius_m * shaft_rpm / 60`.
Measure the radius/travel over the loaded spool. Do not copy simulated
0.30/0.45 m/s payout/stow rates into this N20 configuration without measurement.

Adding an encoder backend is a functional task separate from cleanup. Shaft ticks
need counts/turn, direction, spool diameter/layering, full-stow reference and
travel limits before conversion to line length. They do not prove release.

### Sensors and mechanism

With props off and real bringup running, use `scripts/check_sensors.py lidar`:
capture targets ahead and to port and verify corrected 0/+90 degree bearings.
Check shadow sectors, range and scan age. Saved GCS mounting calibration takes
precedence over launch defaults. Use `scripts/check_sensors.py camera` to
measure rates, resolution, clipping, exposure and sharpness. Default 1280x720,
30 Hz and exposure 100 are configuration, not achieved performance.

Capture real QR/banner/red-ground/payload images at expected distances, angles
and light. `tests/perception/test_real_corpus.py` skips when data is absent.
Historical simulated pixels/module studies are fixture-specific, not camera
calibration. Detection versus decoded identity and framed banner versus plain
coloured sheet must remain distinct.

On a secured props-off bench with catch tray and power cut, measure retention,
touchdown/slack release, retraction without re-grab, parked clearance and loaded
payout/stow speed. A payload fall after accidental lift does not erase failure.
Record repeated trials and every unsuccessful attempt.

## 7. Operation and recovery

Start props-off with verified configuration and the real calibration profile.
This template starts software; it is not an instruction to arm:

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_LOCALHOST_ONLY=1
export AEROTHON_DELIVERY_CALIBRATION=/absolute/path/to/real-load-profile.json
ros2 launch mission_bringup mission2.launch.py use_sim:=false airframe:=cad \
  fcu_url:=udp://127.0.0.1:14555@127.0.0.1:14556 \
  lidar_port:=<device> lidar_yaw_deg:=<measured> lidar_mirrored:=<measured> \
  camera_device:=<device> camera_hfov:=<measured-radians> \
  camera_exposure:=<measured> params_file:=<absolute-venue-yaml>
```

Connect GCS, verify fresh telemetry/video, apply organiser inputs, supply zone
and inclusion-fence polygons and wait for readiness. Readiness is not physical
qualification. START M2 is explicit and guarded. Record operator, FC, ROS and
camera logs. A command acknowledgement does not prove actuator movement.

Abort is latched and checked each tree tick. The guard includes persistent FCU
loss, requested abort, critical battery, floor violation and excessive attitude.
Stage-aware abort disables avoidance and selects LAND below 1.5 m or RTL higher
up. Success/failure latch until reset. Recovery commands remain available when
readiness is unhealthy. Verify mode, landing and connected disarm after recovery.
Review real FC battery/RC/link/fence failsafes and RTL altitude for overhead
geometry; simulated recovery does not approve a physical recovery plan.
Land/disarm before shutting down companion software. After physical payload
reload, restart the actuator/stack state as needed: mission RESET alone must
not be assumed to clear the winch node's per-delivery release latch.

Troubleshooting:

- No heartbeat: check device/power, single serial owner, baud and UDP endpoint.
- Readiness refusal: inspect the named stale/missing source and organiser input;
  correct the input rather than bypass the interlock.
- Wrong scan direction: stop and recheck ahead/port orientation.
- No banner: inspect colour/frame, actual pose, placement, FOV/exposure and age.
- Slow sweep: measure complete-stack capture/processing/delivery rates on Pi.
- Estimated winch travel without motion: stop and verify driver/FC support;
  the adapter does not verify every hardware command response.
- Unconfirmed delivery: check calibrated stable effort channels, not merely
  a release request, estimated stow or visible payload.
- Stuck/failed stage: retain evidence, verify safe recovery/disarm, diagnose
  the first failure and reset explicitly before retrying.

## 8. Simulation and video

The dev host uses WSL Ubuntu, Jazzy, persistent `~/aerothon_stack` and this
colcon workspace. Use a non-login Bash shell and `/usr/bin/python3` to avoid
unrelated Python environments. `scripts/install_ardupilot_overlay.sh` builds
the upstream ArduPilot/Gazebo overlay. It stays off the Pi.

Offline verification is `bash scripts/run_tests.sh --reduced-scope`, covering
regression, syntax/configuration and frontend build. Read the skip ledger;
`--quick` omits frontend build. Known excluded failures remain failures.
The native gateway tests need `pymavlink`, which the distro Python lacks: set
`AEROTHON_NATIVE_PYTHON` to a `--system-site-packages` venv that adds it and
pytest-asyncio (the dev host's is
`.scratch/pi_remote_runtime_20261014/testenv/bin/python`). In a non-login WSL
shell put the nvm Node `bin` on `PATH` for the frontend step.
For each reduced run set `AEROTHON_OFFLINE_SCOPE_EVIDENCE` to a new JSON path
under `logs/`. The scope ledger refuses overwrite; reusing its default path
can fail collection before any test executes. Preserve the earlier ledger.

Fresh rendered acceptance template:

```bash
export AEROTHON_RENDER_CONDITIONS=field AEROTHON_ACCEPTANCE_DOMAIN=30
export AEROTHON_SITL_PORT_SHIFT=100
export AEROTHON_GCS_PRESET='Aerothon 2026 sim h115_both'
export AEROTHON_GCS_PRESET_FILE="$PWD/sim/arena_presets/aerothon26_h115_both.json"
bash scripts/run_recorded_acceptance.sh sim/worlds/clarified_h115_both.json \
  20261004 "$PWD/logs/new-field-both-run" "$PWD/logs/delivery_profile_20261005.json"
```

The wrapper refuses competing simulators/existing outputs, owns its process
group and starts only after independent recorder readiness. Dimensions reach
the aircraft through the GCS path with confirmation. The field preset uses
4 m/s wind, 2 m/s gust amplitude and camera/lidar/FCU degradation. These are
test inputs, not a physical flight envelope. The recorded wrapper accepts
calm/field; strong-gust/worst tests remain outside the selected video scope.
For stopping an active simulation, request ABORT through its GCS and let the
recorders observe actual disarm before shutdown. The current wrapper's TERM
cleanup trap can continue execution after handling a signal; a TERM to the
harness alone is not a reliable pre-arm cancellation. Identify and stop only
the owned process group after verifying the flight state. This known launcher
limitation is retained rather than changed as part of flight-code cleanup.

The requested challenge uses the narrow clarified combined-banner arena and
its return slalom in field conditions. This is the selected hard tested-arena
case, not an exhaustive ranking of all worlds. Keep its actual outcome.

Review `summary.json`, `grade.json`, source/runtime receipts, decision-input
audits, native truth/contact/canary evidence and camera timeline through disarm
together. Video is not a grade. External overview camera data is evaluator-only.
Record the source identity, conditions, independent result and playable video.
Keep interrupted/failed runs unchanged. Original navigation campaigns require
their own five specified rendered gates; see the campaign CLI/source.

## 9. Hardware qualification

Record date/operator, source/configuration hashes, Pi OS, FC firmware, mass,
power/wiring, camera/sensor identity, pass criteria and raw evidence for:

1. Pi boot/restart, complete-stack rates, memory/CPU/temperature and latency.
2. FC electrical link, reconnection, command acceptance and serial ownership.
3. Real camera/lidar calibration, range/noise, frames, rates and capture age.
4. Servo movement, winch driver/travel/stop and implemented encoder acquisition.
5. Props-off link loss, stale data, battery, restart and operator stop behavior.
6. Loaded/unloaded hover effort, command transport, response, braking and pose
   noise. Bench electrical checks cannot qualify hover; measure baro drift too.

After bench review, supervised flights add one capability at a time: open-field
hover, small GUIDED response steps, keep-out, QR/banner, one gate, corridor,
delivery, reduced/full mission. Review each before advancing. The pilot keeps
manual takeover. `scripts/measure_vel_response.py` commands motion and belongs
to flight trials, not props-off software checks. Actual loaded/unloaded data
is processed by `scripts/calibrate_delivery_load.py` into a frozen profile.

Stop on altitude divergence over 0.5 m, frequent open-air keep-out, unsettled
actuators, repeated stages, stale data or loss of control. A horizontal lidar
is not a height reference. Review height sensing and physical failsafes separately.

## 10. Maintenance and historical archive

Original documentation is in
`.scratch/pi_consolidation_20261013/historical_documentation.zip`;
`baseline.json` records original paths/hashes. Later cleanup receipts identify
changes. Historical content can contradict current implementation; interpret
it by source version and date. Developer tools/skills and all qualification
evidence stay local and outside the runtime ZIP.

Cleanup removes only proven unused bindings/dependencies and duplicate metadata.
Keep algorithms, reserves, tests, dynamic imports and runtime resources. A
filename containing `candidate` or `trial` does not establish disuse. Maintain
operational knowledge here and agent workflow in `AGENTS.md`. New qualification
receipts are JSON/run artifacts; update this dated status instead of creating
a third maintained guide. Never edit old source manifests to turn a failure
into a current-source pass.
