# Field readiness: from simulation to the first real flight

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
| Headless closed loop | the real mission tree, navigator, camera and winch nodes against `sim/headless_world.py` (kinematic airframe, ray-cast LD06, object-level detectors calibrated to the real ones, wind, GPS/baro/IMU error, glitches) | the whole mission under any `conditions`, many seeds, in minutes | `python3 sim/fly_headless.py sim/worlds/*.json --conditions worst --seeds 1-5 -j 3` |
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

1. **Software.** On the Pi 5, set up [SETUP.md](SETUP.md) §2, including the
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

- **Wind.** Mean wind at or below 8 m/s and gusts at or below 12 m/s, the
  worst preset's envelope. Above that, nothing here has been tested.
- **Battery.** Pack at or above 15.0 V at rest (the readiness interlock
  refuses below that).
- **GPS.** 12 satellites or more.
- **Organiser's inputs.** Geofence and delivery zone loaded. The GCS
  readiness panel shows both.
- **Sensor launch arguments.** `lidar_yaw_deg`, `lidar_mirrored`,
  `camera_exposure` and `target_marker_m` are set to the day's measured
  values.
