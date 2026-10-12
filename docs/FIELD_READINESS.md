# Field readiness: from simulation to the first real flight

## Current qualification status, 2026-10-07

The latest full offline suite passes 1376 tests with 3 skipped. Syntax,
configuration and frontend checks also pass. The decision-producing source
still matches the archived standard calm seeds, both of which pass all 22
checks. Headless observation/receipt/terminal recording and runtime-capture
output scope have been repaired; their focused regressions pass.

Broader qualification remains failed. The archived-source matrix closed 200
requested combinations with 160 executed, zero navigation passes and 40
classified without flight. A fresh corrected headless calm my_world seed 1
trial still fails return recovery and 0.70 m clearance. Coupled gust/control
qualification remains open. Fresh full rendered shipped, rotated and split
courses are active after the repaired runtime capture. Evidence and current
coordination are in logs/reliability_observation_and_capture_qualification_20261007.
Hardware and staged flights remain deferred and unqualified.

## Archived standard pair qualification, 2026-10-06

Both current-source full standard calm seeds now pass all 22 checks. Seed
20261003 takes 865.0 s with 0.7258271521 m corridor clearance; seed 1001 takes
880.0 s with 0.7130100272 m. Their restricted-zone clearances are 1.5967184497 m
and 1.6248532894 m. Motor confirmation, input isolation, camera through fresh
connected disarm and verified exact source/runtime evidence pass. The latest
complete offline suite passes 1367 tests with 3 skipped; all syntax,
configuration and frontend checks pass. Changing gusts with delayed control,
broader campaigns and additional rendered courses remain under qualification.
Hardware and staged flights remain deferred and unqualified.

## Earlier archived tests

The latest bannerfix repeat failed the return corridor at 0.684245767 m
independent clearance. It entered RTL; recording stopped at 929.515 s while
still armed, before landing/disarm. Six checks fail. Its partial video and
exact 752-file archive are preserved. It is not a full acceptance pass.

Parallel diagnosis fixed a verified FCU sample-time mismatch. Three archived
regressions fail; 31 current related checks pass. The mismatch explains only
part of the recorded response error. Current production/tests are frozen for
the full offline suite before a focused rendered repeat from this failure's
FCU entry. No clearance/reserve change was made. The task-scoped background
launcher is tested with harmless processes; it has not yet qualified a full
recording. Hardware qualification and flights remain deferred.

The most recent full standard run completed and disarmed, passing 21/22
checks. Its sole failure was 965.0 s flight against the unchanged 900 s limit;
corridor clearance was 0.723653986 m and restricted-zone clearance
1.635075236 m. Fresh motor-qualified delivery and input isolation passed.
The complete video and exact source are preserved. This is not full acceptance.

The return-banner search rejected an actual oblique camera view at board
aspect 0.82. A captured-frame regression fails before the measured aspect
floor change from 0.9 to 0.8. All 209 banner regressions now pass and the
package rebuilt; lidar alignment and clearance gates remain unchanged. A fresh
full calm seed 20261003 bannerfix run is running on frozen source. Both
current-source standard seeds and a renewed full suite remain required before
broader qualification. The 1336-test suite below predates this banner change.

Earlier results below are chronological evidence for their archived source.

The latest focused rendered return passed all six checks at 0.739236132 m
minimum clearance, completed the full corridor below the walls and disarmed.
All 170 recorded navigation decisions used fresh actual FCU EKF velocity;
maximum recorded age 0.069 s. The complete video and exact 752-file source
archive verify. This qualifies the focused return only. The full offline suite
and both full standard seeds must pass on this source before campaigns.

The full current offline suite now passes 1336 tests, with 3 skips, in
680.27 s. Syntax, XML/YAML and frontend checks also pass. The full calm standard
seed 20261003 recording is running; full-mission qualification remains pending.

Current-source full acceptance is not qualified. The fresh calm seed 20261003
run failed on return, reporting STUCK and independent clearance 0.680769329 m.
It returned by RTL and disarmed. Delivery motor qualification passed, with
inconclusive visual ground support. Issue 16 tracks the recorded return
failure. Its full video, separate native truth and verified 750-file source
archive are preserved. The broader campaign gate remains closed.

Before the latest yaw/receipt changes, the offline suite passed 1323 tests,
with 3 skips. That whole-suite result needs a fresh run. The focused 117
geometry/stress/delay checks pass. Coupled delay/gust probes still fail under
issue 15. Offline passes do not override the rendered clearance failure.

The yaw/receipt controller passed 61 corridor regressions and rebuilt. The
physical fixtures now queue yaw with velocity and convert body velocity once
at receipt, matching the installed ArduPilot handler. Headless frame tests
passed 7/7. A repeat rendered return is required; no rendered fix is claimed.

The two passing standard runs described below qualify older archived source.

Work is simulation only. Full rendered standard `my_world.json`, calm seed
20261003, passed all 22 acceptance checks in 864.1 s, with 0.74146 m corridor
clearance and 1.56742 m restricted-zone clearance. Seed 1001 also passed all
22 checks in 888.0 s, with 0.76247 m corridor and 1.63821 m restricted-zone
clearance, using the same drone source and frozen motor profile. Both landed
at home and disarmed. Those records satisfied the gate for their archived source.

Those passes qualify their archived source. Subsequent gust regression work
changed avoidance motion certification to include the measured disturbance
trend. The minimized dirty and late-scan failures now pass at 0.77850 m and
0.75809 m respectively. Broad checks and fresh rendered qualification of
that controller change must pass before the next campaign. Its first fresh
full run failed, as recorded above.

The 117-check broad selection now passes, including the original gust
regressions. Two additional probes coupling gusts with physical 0.4 s command
transport still contact obstacles. Those are failures on feasible geometry,
not infeasibility classifications. They remain open under simulation issue 15.
No combined delayed-gust or current worst-condition qualification is claimed.
Older worst-condition findings below are historical. Two subsequent gust
regressions remain unresolved. Headless physical command timing now matches
its controller's 0.4 s delay, with 100 related checks passing. Full offline
and broader fixture/weather runs are in progress. No current
whole-suite or worst-condition qualification is claimed.

Headless navigation does not qualify rendered perception or motor-based
delivery. Delivery now uses calibrated FCU motor outputs first, with onboard
camera evidence recorded separately. An inconclusive camera view must not
be reported as dual-channel agreement. After three unsuccessful attempts,
the drone fully retracts the hook according to commanded travel estimates,
then continues with delivery marked unconfirmed. Estimated travel is not
measured hook position.

Hardware and flights remain deferred. The wiring and settings described
below are proposals until measured and reviewed. Do not load guessed output
assignments. Record connected-hardware evidence using
[HARDWARE_QUALIFICATION_RECORD.md](HARDWARE_QUALIFICATION_RECORD.md), beginning
with props-off checks. Actual loaded/unloaded hover trials are required to
qualify the load signal; props-off bench data cannot establish it.

The simulator can show that the software survives conditions. It cannot
show what the real aircraft is. This page lists what has been proven in
simulation, then everything that must be measured or set on the real
aircraft before the stack is trusted with a flight. Work through it in order.
Nothing on this list can be done from a laptop.

## 1. How the stack is tested (the pyramid)

Industry practice for "works on the first real flight" rests on three
things. The first is domain randomisation: test against a spread of
conditions wider than reality, not against one clean world. The second is
fault injection into the flight controller. The third is a ladder of
fidelity, where each rung is cheap enough to run many times.

| Rung | What it runs | What it proves | Command |
|---|---|---|---|
| Unit / stage | each detector, stage and rail against fakes and synthetic scans | logic, fail-closed rails, every corruption severity the detectors are held to | `python3 -m pytest sim/ tests/` |
| Headless closed loop | navigation nodes against a kinematic airframe, ray-cast lidar, object-level detections and sensor corruption | navigation within the declared model; no rendered perception or motor-delivery qualification | `python3 sim/run_navigation_campaign.py --help` for the gated campaign |
| Gazebo + SITL | ArduPilot's own EKF and controllers, rendered camera through `degrade_node`, the LD06 plugin | the real flight-controller behaviour: EKF glitch rejection, failsafes, mount and winch commands | `scripts/run_custom_world.sh NAME --conditions worst --seed 3` |
| Bench (this page, §2) | the real Pi 5, sensors and Pixhawk, props off | wiring, drivers, frames, parameters | `scripts/check_sensors.py` |
| Build-up flights (§4) | the real aircraft, one capability at a time | the numbers simulation assumed | — |

The `conditions` presets (`scripts/world_spec.py`) are calm, field, worst
and random. "random" draws every factor between calm and worst, with wind
from any heading. Worst is 8 m/s wind with 4 m/s gusts and 20° of veer;
severity 2 of every camera corruption at once, with 20% of frames dropped
and 150 ms of latency; lidar at 3 cm noise, 10% dropout and 1% false returns;
a faded, dusty banner and QR prints; a 5 m GPS glitch mid-search; 3 mm/s baro
drift; and a battery at 3.85 V/cell.

What the worst campaign found and fixed is in the git history under
"Worst-day fixes". In brief:

- A companion-side lidar keep-out now covers every position setpoint.
  ArduPilot's own proximity avoidance does not run in GUIDED.
- A terminal failure now RTLs instead of hovering until something moves it.
- The square-up's tolerance widens when GPS wander makes 5° unattainable.
- The gate stage now trusts the square-up's own sighting of the board.
- The battery thresholds are now for Li-ion, not LiPo.

## 2. Bench checks (props OFF)

1. **Software.** On the Pi 5, set up [SETUP.md](SETUP.md) §2a, including the
   perception line: `tesseract-ocr libzbar0 python3-pyzbar`. Without
   tesseract the banner is never identified. Without zbar every QR goes
   through the slower OpenCV path, and `qr_node` warns at start-up. Also
   install the LD06 driver (`ldlidar_stl_ros2`, built from source into the
   workspace) and `ros-jazzy-usb-cam`.
2. **Flight-controller parameters.** Load
   `src/aerothon_sim/sim_gazebo/config/aerothon_failsafe.parm` in Mission
   Planner. The battery lines are for the 4S2P Li-ion pack:
   - low 12.8 V, critical 12.0 V;
   - sag-compensated (`BATT_FS_VOLTSRC 1`, which needs the power module's
     current sensor calibrated);
   - held for 10 s before they act.

   Set `BATT_CAPACITY` to the pack's rated mAh, so the percentage the
   mission also watches is real.

   Then load
   `src/aerothon_mission/mission_bringup/config/aerothon_hardware.parm`.
   It configures the companion port (TELEM2 at 921600), the tilt servo as a
   MAVLink-targeted mount and the PWM winch. Without it, the stack's mount
   and winch commands are accepted and do nothing. Its servo output
   numbers are a guess at the wiring, so edit them first.
3. **Lidar mount.** Launch with `use_sim:=false`, then run
   `python3 scripts/check_sensors.py lidar`. It asks for a box ahead of the
   nose and then one to port, and prints `lidar_yaw_deg:=… lidar_mirrored:=…`.
   Put those in the launch command. Every scan consumer reads bearings off
   the nose. A lidar mounted 90° off would have the navigator steer into the
   walls it is avoiding. `sim/test_scan_mount.py` pins the correction.
4. **Camera.** Run `python3 scripts/check_sensors.py camera`. You need
   1280×720 at 15 Hz or more with manual exposure. The launch default is
   `camera_exposure:=100`, which is 10 ms. Auto exposure on a C270 runs to
   60 ms or more in shade, which smears a QR by about 20 px at sweep speed.
   If the frame is dark at 10 ms, raise the exposure in steps of 20. Do not
   switch to auto.
5. **Camera tilt.** Command each pose from the GCS and watch the servo.
   `/camera/pose_state` reports `"readback": "mount"` if the Pixhawk streams
   a mount attitude, or `"timed"` otherwise. Timed means the servo is assumed
   to be at its angle `servo_settle_s` (1.0 s) after the command. Time the
   real servo's worst move, NADIR to FORWARD, and set `servo_settle_s` above
   it.
6. **Winch.** Run a full drop and retract on the bench with the real 100 g
   payload, 10×5×5 cm. Check that the hook releases on touchdown.
   Nothing reads the line length back (PWM winch, no encoder): `winch_ctrl`
   integrates it from `payout_rate_mps` and `stow_rate_mps`. Time a known
   length each way and set both in
   `src/aerothon_mission/mission_bringup/config/venue.yaml`. If the winch
   is slower than the setting, commanded travel can overestimate deployment
   or full stow. Those estimates do not establish touchdown or detachment.
   The delivery observer establishes loaded hover, lowers, assesses load
   reduction, commands a short retraction probe, and requires qualified
   unloaded telemetry after full estimated stow. Load returning or observed
   payload rise causes another lowering attempt. Three failed attempts lead
   to full estimated stow and unconfirmed mission continuation.
   The onboard payload finder uses colour and apparent size. Check its
   actual acquisition, tracking and range estimates with the real payload
   before selecting camera settings. `visible: true` alone does not qualify
   ground support or release. Freeze motor/load thresholds from separate
   actual loaded and unloaded hover trials before acceptance flights.
7. **CPU budget.** Run `python3 scripts/bench_perception.py` on the Pi 5
   with the stack stopped. On a 2.1 GHz Xeon core, the NADIR set (QR on
   bare grass, the red-zone mask and the payload finder) came to 47 ms
   (21 Hz), and the banner check to 27 ms. The QR reader is the slowest
   node at 37 ms on an empty frame. A Pi 5 core runs this kind of code
   1.5–2.5× slower. Below the 10 Hz target the search still works, but
   sweeps more slowly, because its speed comes from the measured frame
   rate.

## 3. Things the simulation could not settle

- **Baro drift.** The mission has no height reference except the flight
  controller's barometer; the LD06 scans horizontally. Warm-up is the
  largest real drift. Power the Pixhawk at least 5 minutes before arming, and
  cover the baro with open-cell foam against prop wash and sun. Worst was
  flown at 3 mm/s. At 20 mm/s the banner stage was flown with the aircraft
  2.6 m lower than it believed. **Strongly recommended:** a downward
  rangefinder (a TF-Luna or VL53L1X, a few grams) with `RNGFND1_*` and
  `EK3_RNG_USE_HGT 70`. That makes the low stages (gate crossing, winch)
  immune to drift.
- **`vel_response_s`.** This is how fast the airframe follows a velocity
  command. The corridor navigator's wind observer depends on it. At 1.0 s
  against the simulated 0.6 s, the tight 1.7 m slalom in a gusty crosswind
  still touched (`sim/test_corridor_stress.py`). Measure it (§4, step 2).
- **Real images.** The detectors are calibrated on rendered frames with
  synthetic corruptions. Shoot the real corpus in
  [CORPUS_SHOT_LIST.md](CORPUS_SHOT_LIST.md). `tests/perception/test_real_corpus.py`
  picks it up automatically.
- **GPS glitches.** The headless world models the EKF3 innovation gate.
  A jump of more than 3 m is rejected, and the estimate dead-reckons at
  0.1 m/s until the GPS agrees again. If the GPS is still rejected after
  10 s, the estimate resets onto it. The real numbers depend on
  `EK3_POS_I_GATE` and the IMU, and only Gazebo SITL (`SIM_GPS_GLITCH_*`,
  from the `conditions` block) runs the real EKF. Before the gate was
  modelled, a 5 m glitch passed straight into the estimate and the red-zone
  map was drawn 5 m off.
- **Red-zone clearance.** Red zones are kept 1.5 m clear
  (`redzone_clearance`). That is about 2σ of GPS wander at the readiness
  interlock's HDOP of 1.2 or less. On a day with worse GPS, raise it.

## 4. Build-up flights

Fly one new capability per flight, with a pilot on the RC switch holding
LOITER/LAND, in an open field first.

1. **Hover.** Fly LOITER at 3 m for 2 minutes. Check that
   `/mavros/local_position/pose` agrees with a tape to within 0.5 m.
   Afterwards, read how much the altitude wandered while holding.
2. **System ID.** In GUIDED at 3 m, run
   `python3 scripts/measure_vel_response.py`. It makes four 0.5 m/s sideways
   steps, no more than 2 m of travel. Then run
   `ros2 param set /velocity_controller vel_response_s <printed value>`, and
   put that value in the launch.
3. **Keep-out.** In GUIDED hover, walk a 1 m board toward the aircraft from
   the side. The log should show `KEEP-OUT` and the aircraft should back off
   to 1.0 m. This is the rail that stops a GPS-held hover drifting into a
   wall.
4. **Start QR and banner.** Print the start QR and a full-size banner. Fly
   the mission up to BANNER_ALIGN at a single gate, and abort from the GCS
   after SQUARE ON.
5. **One gate.** Fly through a gate built to the rulebook's dimensions,
   first in calm air.
6. **Delivery.** Fly the lawnmower search over printed pads and do the
   winch drop.
7. **Full mission.** Fly the full mission at reduced scale, then at full
   scale.

Stop and investigate on any of these:
- an `ALTITUDE DIVERGENCE` over 0.5 m;
- more than one `KEEP-OUT` per minute in open air (a lidar speck, or a
  bracket in the scan);
- a camera `readback` that never settles;
- a stage retrying the same step.

## 5. Go / no-go on the day

- **Wind.** A flight wind/gust envelope is still unqualified. The 8 m/s mean
  and 12 m/s peak preset values describe test inputs. Current coupled
  delay/gust diagnostics breach clearance (issue 15). Set flight go/no-go
  limits only after reviewed simulation and measured hardware response trials.
- **Battery.** Pack at or above 15.0 V at rest (the readiness interlock
  refuses below that).
- **GPS.** 12 satellites or more.
- **Organiser's inputs.** Geofence and delivery zone loaded. The GCS
  readiness panel shows both.
- **Sensor launch arguments.** `lidar_yaw_deg`, `lidar_mirrored`,
  `camera_exposure` and `target_marker_m` are set to the day's measured
  values.
- **Venue file.** `mission_bringup/config/venue.yaml` holds the real
  banner size, return-lane offset, payload size and colour, and the
  timed winch rates. It ships with the simulator's values.
