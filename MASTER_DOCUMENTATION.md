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

### 16 October 2026: real-drone bring-up and real-path audit

The deployed Pi (props-off bench, FC on TELEM3) showed no lidar in the SLAM
tab. The fitted lidar is an RPLIDAR C1, not the LD06 the launch started; the
C1 only spins after its driver's start command (section 5). Three read-only
audits then traced the real-aircraft path (GCS and web host, flight logic,
sensors and actuators) for defects that Gazebo hides. Fixed, each with a
regression test (`sim/test_real_path_wiring.py`,
`sim/test_mav_router_broadcast.py`, `tests/test_web_robustness.py` and
additions to the camera, winch, GPIO-winch and vertical-motion tests):

- Sensors and GCS: readiness heard `/scan` RELIABLE against a BEST_EFFORT
  publisher (lidar rate 0 Hz for ever); QR read `/camera/camera_info` while
  usb_cam publishes `/camera_info`; images carried an undefined frame; one
  non-finite telemetry value (`front_m` inf with nothing ahead) made the
  browser reject every frame; the SLAM tab now shows the live scan and why
  no map exists; devices plugged in after boot reach the container.
- Web host: the aggregator listener could die silently (all commands then
  refused as stale); a Start the runtime refused wedged later Starts; a
  corrupt `profiles.json` crash-looped the GCS; one log handle leaked per
  Connect; non-JSON errors; the router supervisor relaunched a dying router
  every 0.5 s. The web-host tests had been skipped wherever pytest-asyncio
  was missing; `tests/conftest.py` runs them.
- MAVLink router: FC MAVLink is also broadcast on each operator LAN at UDP
  14550 (section 6), so Mission Planner in UDP mode needs no laptop IP.
- Flight logic: arming retried for ever (an aircraft could arm itself once
  a pre-arm condition cleared) -- now 20 s then FAILED; a pilot switch to
  LOITER/ALT_HOLD/POSHOLD was not an intervention, so a later failure could
  command RTL over the pilot; Takeoff compared height above the EKF origin
  with a target above home and had no timeout; organiser fence, zone and
  route points were converted about home but checked about the EKF origin
  (they differ on hardware), and the uploaded FC fence is converted back;
  Abort while idle failed the next flight; the operator target persisted
  into the next run and never reached the mission (`/mission/target_override`);
  `/mission/state` kept the last stage after a run; avoidance tasks waited on
  the camera actuator they never use; the mechanism task hung if winch
  status stopped.
- Actuators: camera tilt reported settled with timed read-back although the
  FC never accepted (or never received) the command; camera buttons sent
  degrees that no detector gate recognised; the MAVLink winch estimated
  0.30 m/s while ArduPilot's length control reels at `WNCH_RATE_MAX` (1.0),
  now 0.30 on both sides (`fc_rate_max_mps`, `aerothon_hardware.parm`; the
  parameter names and the simulator's rate were only corrected on 20 October,
  see "20 October 2026" below), and
  counts only after an accepted `DO_WINCH`; the GPIO encoder lost counts when
  lgpio delivered edges in batches.
- Avoidance: one vertical-motion capture gap longer than `stale_scan_s`
  latched a fault that also made `_velocity_fresh()` false for the rest of
  the traversal, freezing the aircraft in a corridor until the battery
  failed. Gaps up to 3x `stale_scan_s` are now bridged with the FCU
  velocities either side (no barometer trust); longer gaps still latch.

Evidence on this source (uncommitted worktree on `9e4cee6`; diff and hash in
`logs/e2e_final_20261016/worktree.*`): reduced offline 2,062 passed, 8
skipped (`logs/reduced_c1_20261016e.log`, ledger
`logs/offline_reduced_scope_c1_20261016e.json`); native 9 passed with
pymavlink; frontend 25 passed, typecheck and build. Headless
navigation-only campaign, arena through each world's GCS preset,
`logs/e2e_final_20261016/`: calm 23/24 across all eight clarified worlds
(corridor 0.717-0.786 m, red at least 3.36 m, 609-687 s); field 10/12 on the
h030 worlds (two h030_ground corridor clearances 0.617 and 0.687 m). The calm
failure is GateAdvance failing closed ("scalar speed capture differs from
vector history") under CPU load. A same-batch A/B on h115_both
(`logs/ab_20261016/`) gave identical results for `9e4cee6` and this source
before the gap fix (both froze on seed 5); with the fix the frozen seeds pass
(`logs/gapfix_20261016/`). Headless runs omit delivery (no motor model), so
delivery is still qualified only by the rendered runs above.

Later on 16 October, approved by the user: gate braking no longer aborts the
mission on the first late or skewed FCU velocity capture. A braking gap up to
`bridge_s` (3x `stale_s`, 0.9 s) is integrated between the captures either
side; a capture stamped ahead of the node's clock (MAVROS timesync, `/clock`
lag) is a transient; a transient fault holds the last braking anchor for up
to `pause_s` (2x `stale_s`, 0.6 s), as does the stage-level capture pause;
invalid data, a gap beyond 0.9 s, or a fault outlasting the pause still fail
closed. Stream requests (`stream_rate_keeper`, `scripts/set_stream_rates.py`)
were cut from about 7.2 to 4.2 kB/s of the 11.5 kB/s TELEM3 link: ATTITUDE
and LOCAL_POSITION_NED 25 Hz, GLOBAL_POSITION_INT 5, GPS_RAW_INT 2, VFR_HUD 4,
SYSTEM_TIME 2, RAW_IMU 2; SERVO_OUTPUT_RAW stays 20 Hz (delivery
calibration). Headless runs have no MAVLink link, so the rate cut is verified
only on SITL or the aircraft. Mission Planner on the same serial link can
re-raise streams through its own rate settings; keep its telemetry rates low.
The lidar and camera drivers respawn. `camera_exposure` applies the
`camera_exposure` launch argument through the current UVC control names
(`auto_exposure`/`exposure_time_absolute`; usb_cam 0.8's `exposure_auto`/
`exposure` are rejected). The default 0 keeps aperture-priority auto
exposure: a forced 10 ms manual exposure with gain 0 made the Brio 100 feed
very dark on 16 October. Set a positive value only after measuring it.

The campaign for this change (`logs/e2e_gatepause_20261016/`, same worlds,
seeds and presets as `e2e_final`) does not qualify it either way. Calm 15/24
and field 7/12; nine runs ended "ReturnCorridor: corridor navigator reported
STUCK" after the velocity controller found no gap. The old GateAdvance abort
did not recur. The onboard nodes were CPU-starved: 258 lidar receipt gaps
over 0.3 s against 4 in `e2e_final`, with receipt lag p99 up to 0.20 s against
0.01-0.02 s, although the world kept 2x sim time. Velocity controller and
corridor source were byte-identical between the two campaigns, and the
change cannot delay scan delivery. The same-batch A/B
(`logs/ab_gatepause_20261016/`, receipt and `ab_summary.*`) flew A
(`9e4cee6` plus the `e2e_final` diff) beside B (this source as deployed).
Starvation was light and equal: lidar gaps over 0.3 s were 30 (A) and 38 (B),
with receipt lag p99 at most 0.14 s. B passed 29/30 and A 25/30: calm 24/24
against 22/24, and field h030_both/h030_ground 5/6 against 3/6. Every seed A
passed, B passed too. Fisher p is 0.195, so this shows no regression, not a
demonstrated gain: neither arm hit a GateAdvance abort. "ReturnCorridor:
corridor navigator reported STUCK" occurred three times in A (once with no
receipt gaps) and once in B. It predates this change and remains an open
corridor issue. Laptop standby interrupted field h030_suspended (kept under
`interrupted_standby/`), and field h030L5_both was not flown; both remain to
fly on AC power. The reduced suite passed 2,070 with 8 skipped. The frontend step failed only
because the non-login WSL shell had no `node`; run with the nvm Node, it
passed (25 tests, typecheck, build; `frontend_build.log`). The aggregator
now takes camera frames serialized (`raw=True`) and reads only the header
stamp.

Still open from the audits: the camera-actuator gate stays closed on the
aircraft until tilt feedback is qualified (all flight tasks except
avoidance are refused); `stream_rate_keeper` asks for about 60% of the
115200 TELEM3 link; the C1 mount yaw/mirror is unmeasured; the fitted
camera is a Logitech Brio 100, not the C270 the field of view
(`camera_hfov` 0.8519 rad) and exposure were set for, so measure both; Pi 5
supply (below); offline
map tiles beyond the regions in `scripts/map_regions.json` are absent; the EKF-datum display and Graphs
sensor rates are empty on the aircraft; SLAM needs FCU local position (GPS
fix) for its odometry.

Pi 5 power, measured 16 October (synced logs in
`/home/pi5/.local/state/aerothon/power_log_*.csv`, `kmsg_*.log`,
`loadtest_*.csv`): every disappearance that day was a cold power-on
(`power_reset` 0). With the runtime connected the supply fell from 4.97 V
to 4.69 V in 19 s, the kernel logged `Undervoltage detected!` and the Pi lost
power. A guarded step test: idle 4.98 V, C1 spinning 4.995 V (the lidar is
not the load), two CPU cores 4.76 V within 12 s, still falling after the load
stopped, then a loss at idle. The supply negotiated only 3000 mA on both the
original and the replacement supply. The CPU itself is stock (no
over_voltage, 2.4 GHz, ondemand). An earlier session had added
`usb_max_current_enable=1` (USB ports 1.6 A instead of a shared 600 mA,
backup `config.txt.before-usb-current-20261016`). It was reverted at 23:29
at the user's request. Boot still logged under-voltage at 5 s and 37 s, and
idle held 4.97-5.08 V, so that setting was not the cause. Restore it
(`config.txt.with-usb-current-20261016`) if the C1 and camera drop out
together at 600 mA. Later that night the Pixhawk was silent on TELEM3: the
UART counted 0 bytes. GPIO14 (Pi TX, header 8) stayed at 0 V even with a
pull-up, and GPIO15 (Pi RX, header 10) followed whichever pull was set.
So the FC TX was not driving the line, and the Pi TX was clamped low: an
unpowered FC/TELEM3, or disturbed wires next to the 5 V/GND pins 2/4/6.
`pinctrl` with the router stopped tells these apart. Use the official 27 W (5.1 V 5 A) USB-C supply
with its own cable, or a dedicated 5.1-5.2 V 5 A BEC on short heavy wires
(then `PSU_MAX_CURRENT=5000` in the EEPROM), before any further runtime or
flight work. The lidar and camera drivers now respawn, since a driver that
exited (device absent at Connect, USB reset after a brown-out) left the C1
still until the next Connect.

From 12:09 to about 19:20 on 16 October the C1 head answered nothing. sllidar
logged `SL_RESULT_OPERATION_TIMEOUT` on every respawn, across three USB
ports. With the driver paused, a raw probe got zero bytes at 460800, 115200
and 1,000,000 baud and after RESET, while the CP2102N adapter enumerated
and accepted writes. After the user reconnected it and the Pi then
cold-restarted, GET_INFO returned model 0x41, firmware 1.02, hardware 18, the
same serial, and GET_HEALTH status 0. So a silent C1 behind a healthy adapter
is a wedged head or its lead, not a driver fault: reseat the adapter-to-lidar
cable or power-cycle the lidar. The kernel's `cp210x ... failed set request
0x12 status: -110` (PURGE at port close) also appears while the lidar
answers normally; it is not a fault indicator.

Night of 16-17 October, Pixhawk link and rebuild. Mission Planner connected
but stalled at "Getting params". The router was proven correct: 200 laptop
frames all reached the UART. The FC returned only heartbeats (about 21 B/s
against 58 B/s of requests). GPIO14 (Pi TX, header 8) read high even when
driven low, while free GPIOs passed the same test. So that output stage or
its wire is suspect. The link moved to UART2: `dtoverlay=uart2-pi5`, GPIO4
TX (header 7) to TELEM3 RX (pin 3), GPIO5 RX (header 29) from TELEM3 TX
(pin 2), `/dev/ttyAMA2` at 115200. The Pi's SD slot then failed: two
different cards timed out at `mmc0: error -110 whilst initialising SD card`
and dropped to `(initramfs)`. The bootloader still read them, but Linux
could not. The Pi now boots Debian 13 from a USB 3 drive (`/dev/sda`) with
the SD slot empty; BOOT_ORDER `0xf461` is unchanged. Because the boot drive,
C1 and camera share USB on a supply without PD, `config.txt` sets
`usb_max_current_enable=1` (backup `config.txt.before-aerothon-20261017`).
The router LAN has no Internet, so the rebuild ran through the temporary
loopback-only SSH proxy. A 12 s first DNS lookup on the laptop needs
timeouts above 10 s, and the laptop must stay on wired Ethernet: its Wi-Fi
kept hopping to the receiver's "ExpressLRS RX" access point. The rebuild
followed section 5: Docker 26.1.5, `aerothon-dependencies:20261014` and
`aerothon-runtime:20261014` from this source, the C1 driver at `34300099` and
the LD06 driver at `bf668a89` (pthread patch). colcon finished 14 packages,
`run_container.sh check` passed everything, and the services were enabled.
The GCS profiles were recreated: drone on `/dev/ttyAMA2` with SLAM, and
laptop-sim at the laptop's current address. "Secured props-off wiring
reviewed" is left for the operator, who must press Save profile before
Connect, because Connect uses the saved copy. The first UART2 wiring put the
FC TX on header 31 (GPIO6, 1 Hz edge bursts) instead of 29. After moving it,
a direct test on `/dev/ttyAMA2` without the runtime got FC heartbeats, and
PARAM_REQUEST_LIST returned all 1,036 parameters in under 25 s.

17 October, boot and LiDAR mapping repair. The Pi's live baseline reproduced
the complaint with zero satellites: C1 at 9.7 Hz, only 72 beams forwarded to
the GCS and no occupancy map. Runtime preparation was still manual. The new
boot connection, full-beam display, mapping-only scan odometry, inclusive grid
bounds and multi-stage measured calibration are described in sections 3, 5
and 6. Native ROS testing with 120 moving room scans and 2 mm deterministic
range perturbation retained all four walls within 0.15 m, put every occupied
cell within 0.12 m of a known wall and marked over 97% of the room interior
as observed free. This is synthetic-scan software evidence, not a physical
calibration or flight qualification. Source/bundle inventories, test ledgers,
Pi deployment, boot/UDP checks and physical scan/map receipts are kept in
`.scratch/lidar_boot_20261017/`. On 18 October the user reported that objects
at the C1's front were drawn behind the GCS arrow. `sllidar_ros2` puts the C1's
0 degrees at pi, and the uncalibrated mount yaw 0 did not undo it, so every
`/scan` consumer saw the scan reversed. `scan_mount` now applies the per-model
driver correction (Sensors and mechanism, section 6). Deployed the same day,
the live scan starts at 0 rad instead of -pi; a physical front/left target
check is still pending. Fresh measured XYZ/tilt and panel captures
are still required for a physical mounting claim.

18 October, GCS testing pass. The user saw the GCS disconnect and reconnect
repeatedly once SLAM mapping started, with the SLAM tab showing an old map.
A local rig (fake FCU, lidar, growing map and execution service; the real
aggregator and web host; `.scratch/gcs_testing_20261018/`) exercised every
Testing task, the organiser inputs, both dialogs and all tabs. Causes found:
the SLAM tab rebuilt the whole occupancy grid on every telemetry frame
(10 Hz), so a slower phone or tablet fell behind the stream and missed the
host's ping window (2.5 s), and the host closed the socket; the page kept its
last grid across reconnects and runtime changes; the aggregator's 1.0 s map
throttle against slam_toolbox's 1.0 s publication dropped about every other
map. Fixed: the grid is rasterised once per map and drawn per animation
frame; the view follows the growing map; slam_toolbox's `/pose` places the
aircraft, its track and the live scan on the map; map age replaces the
Live/Stale flicker; the aggregator and web host replay the newest map to a
reconnecting page and the page drops it when the runtime or profile changes;
the browser heartbeat allows 5 s. Other defects fixed in the same pass: the
web host refused `lidar_cal_geometry` and `lidar_cal_background`, so the
calibration wizard could not pass step 1; a refused Start showed its reason
for 0.2 s before the previous run's republished status replaced it, and
receipts never reached the event log; malformed waypoint text threw without a
message; errors were drawn behind open dialogs; a blocked Start gave no
reason; `index.html` had no `Cache-Control`, so browsers kept an old GCS after
a deploy (pages opened before this fix need one manual reload). Display and
host only: no flight decision changed.

The same day the GCS was driven against local laptop simulation (Gazebo,
SITL and gateway on domain 43; the real web host and production runtime on
domain 42): profile, Connect, organiser inputs, readiness, GUIDED, Arm,
Takeoff, camera tilt, Land, RTL, passive SLAM and QR tasks, every camera feed,
and the SLAM map in flight (live throughout, under 1 s old). Further defects
fixed: Chrome keeps an MJPEG request open after its image leaves the page, so
feed switches, retries and tab visits left streams open and after six the
browser queued every request to the Pi, Stop and Land included, while the
status still read Live FCU (one stream now, released explicitly; API calls
time out after 10 s as Outcome unknown); a feed with no frames showed a blank
box; slam_toolbox publishes `/pose` only after 0.1 m or 0.1 rad of motion, so a
still aircraft lost its marker (the last pose is kept, with its age); Stop and
Abort act only on a production execution and were accepted while a manually
launched aircraft kept hovering (the review now says so and points to Land or
RTL); a refused Start named only "camera (not ok)" (the GCS now shows the
measured rate against the requirement); a runtime that exited at launch left
only "Stopped" (Connections shows it and the runtime log); a hard-killed launch
left its nodes running and Connect started a second runtime beside them, with
the old aggregator holding 8765 and the new one's server thread dead (Connect
now refuses while the old process group has members, Disconnect stops them
behind the same disarm gate, and the aggregator retries its port); a web-host
restart with a page open took about 60 s (now about 10 s). Not GCS defects,
left unchanged: on this laptop the simulated camera reached 8.7 Hz of vehicle
time against the runtime's 10 Hz requirement and the actuator flags toggled
several times a second, so camera-dependent flight tasks were mostly refused;
Banner alignment, once accepted, failed at RequireDeliveryZone although
readiness reported the search area ready (the mission resolves the fence only
after an FCU home position, which was not observed in this run).

19 October 2026, SLAM display refresh and local testing continuation. The map
now uses a larger neutral occupancy view, separate map/lidar/mapping-state
indicators, independent Occupancy/Lidar returns/Track/Grid switches, explicit
Fit map and Follow aircraft controls, an expanding view, cursor coordinates
and an adaptive metric scale. Manual pan releases follow; mouse-centred zoom,
touch pinch and keyboard navigation preserve equal metric axes. Fit scan
includes the sensor's full range at phone width. The design references RViz's
occupancy display, [Foxglove's layers and coordinate frames](https://docs.foxglove.dev/docs/visualization/panels/3d)
and [QGroundControl's vehicle centring](https://docs.qgroundcontrol.com/master/en/qgc-user-guide/settings_view/general.html#fly-view).
The local map labels +X/+Y rather than claiming geographic north. Unknown
cells and the original grid resolution remain intact; the raster is still
cached per received map rather than rebuilt for each telemetry snapshot.

Scan freshness is independent of map freshness. Held or old mapping status,
an old/mismatched pose or unavailable mounting geometry suppresses the
registered scan overlay while leaving Live lidar available. An old marker
is grey and explicitly described as the last mapped position; age does not
prove the aircraft stayed still. Full applied `lidar_calibrated` geometry
projects the corrected scan through the residual mounting tilt and measured
XY translation before the map pose. Yaw, mirror and range correction are not
applied twice. Legacy `base_scan` offsets are not invented. The projection
matched 80 production-quaternion reference cases within 4e-15 m in software.
Phone header overflow is also fixed. Browser checks used a synthetic ROS
fixture and the actual local Gazebo/SITL map; these are distinct evidence.

The local continuation also fixed a refused bench release that prevented a
later safe stop/stow, a release request that could replace a genuine encoder
fault with a transient diagnostic, and successful bench receipts that reused
the previous execution failure reason. Real encoder/backend faults and all
release preconditions remain enforced. The affected backend checks passed
51 tests; the frontend build and 45 frontend tests passed. Evidence, research,
source hashes and final software-check results are recorded under
`.scratch/slam_ui_20261018/`. Flight-navigation algorithms and qualification
thresholds are unchanged.

Local flight results remain incomplete: an accepted avoidance route made
under 1 m progress in 112 s before operator Stop and RTL/disarm. A calibrated
full-mission attempt decoded the start QR and reached banner alignment, but
repeatedly lacked lidar returns for its banner fit and was stopped after a
300 s observation window. The first GPS-delivery attempt at 5 m could not
frame the world's 3 m QR; the corrected 7 m request was refused by measured
actuator-capability gates before arming. Delivery here reached WinchDrop but
reported missing/unqualified load calibration. None is a completed mission or
delivery acceptance. The revised package is intended for props-off Pi software
verification; Pi sensor/mounting verification and flight qualification remain
separate outstanding steps.

### 20 October 2026: laptop-simulation search pace, winch retraction, return banner

All on the world-maker laptop route (`manual_test` world, unlettered rod-hung
banners, orange no-entry boards). Uncommitted worktree on `21ae45b`.

- Search pacing: `camera_ctrl` publishes the measured joint's `rate_dps`;
  `perception_redzone`, for joint read-back only, accepts a fresh (<= 0.3 s),
  non-slewing (<= 15 deg/s) angle and checks the true line of sight against
  its nadir tolerance. The old settle rule compared a body-relative joint with
  the earth-frame mount request and stop-go paced the search at 0.17 m/s.
- Winch: the simulator's FC reeled at `WINCH_RATE_MAX` 1.0 while the estimate
  used 0.30, so "stowed" left 2.6 m of line out (measured joint); the hook
  dragged through the return corridor (stall, 44 deg tilt, sink). Both
  parameter files now set `WINCH_TYPE 1`/`WINCH_RATE_MAX 0.30` (the hardware
  file used the nonexistent `WNCH_*` names). `winch_node` reads the two FC
  parameters back, refuses to lower until it has, estimates with the FC's
  rate, and with a measured line reports stowed only when it is measured in,
  re-sending stow on a stall and faulting after three tries.
- Return banner: the mission ranged banners with the configured 1280 px focal
  while this route's camera delivers 960 x 540. From the return stand-off the
  return board 6.4 m ahead ranged ~10 m and `FindReturnBanner._toward` took it
  for the outbound banner 17 m beyond it on nearly the same sight line; it was
  refused on every frame and the search orbited false leads for ~9 minutes.
  `banner_frame` now ranges with the size of the frame the detection came
  from (`AlignToBanner`, `FindReturnBanner`). The search logic is unchanged
  from V44.
- Speed: corridor cruise 1.0 m/s and the search's braking allowance
  (`search_brake_mps2`, default 0.5) come from the simulation-only venue file.
  The simulated airframe's stop after the search's own hold command was
  measured at 0.54-0.55 m from 1.0 m/s and 0.69 m from 1.2 m/s in four
  directions (0.85-1.06 m/s^2; `logs/return_lap_20261020/brake_probe`); 0.8 is
  used. The search's cap rose from 0.65 to 0.70-0.75 m/s: 1 m/s would overrun
  the 1.5 m red clearance at the 2.5 m look-ahead. The aircraft keeps 0.8 m/s
  cruise and 0.5 m/s^2 until its own stop is measured.

Evidence: `logs/return_lap_20261020/manual_test_winchfix` (winch retracted to
0.2 m, tilt 18.2 deg max; return lap failed on the ranging defect;
operator-stopped, `INTERRUPTED.txt`) and `manual_test_1mps` (14/14 independent
checks: both corridors flown through, 0 lane violations, closest obstacle
0.76 m, closest red 3.45 m, tilt 16.5 deg, drop 0.18 m, payload 0.25 m from
pad B, 509 s, landed 0.47 m from home; return banner identified from the
stand-off 70 s into its search). One calm laptop-simulation run; the scripted
acceptance, field conditions and the aircraft are not re-qualified on it.
Reduced offline suite on the same source: 2,150 passed, 8 skipped
(`logs/return_lap_20261020/reduced_suite_final.log`). Receipt:
`.scratch/return_lap_20261020/receipt.json`.

### 25-26 October 2026: organisers' Track 1 field properties PDF

Source: "AeroTHON 2026 Track 1 Field Properties" (organisers' PDF of 23 Oct,
12 pages; Mission 2 on pages 9-12; SHA-256 `3e9fb5ce...6324dd`), with the
operator's reading "corridor will be 10 feet and banner will be hung till 8
feet". As applied:

- Corridors: two lanes of white-screen walls 22 ft long and 11.5 ft apart,
  10 ft high; the drawing's 10 m length is flown as a second world.
- Boards: entry arch 11.5 x 1.5 ft **green #00B140** with its lower edge at
  8 ft, and a green 11.5 x 1 ft board on the ground at the entry; the same
  pair in **blue #0000FF** at the exit corridor's entrance on the zone side;
  1 in white borders; no orange boards.
- Red zone: one, 10 x 10 ft #FF0000, 1 in border. Exit corridor: three
  3.5 x 6 ft boards on legs. QR: five 1 m codes in the 40 x 30 m zone and one
  at take-off, **no white border**, nothing encoded for the mission. Payload
  100 x 50 x 50 mm, 100 g, lowered from 5 m.
- Not given, and entered as working values to confirm on the day: lane
  spacing 5 m, hall 70 x 45 m, navigation height 1.5 m (under the 8 ft edge,
  and low enough that the lidar stays on the 6 ft boards).

GCS: built-in preset **AeroTHON 2026 Track 1 field (organiser PDF)**; new
fields Ground banner height and Obstacle height; the obstacle visibility rule
(section 4); colour roles with the Exit corridor banner (section 4).

Gaps the field exposed and what changed (flight logic: perception, mission):

- Return lap colour: the return search and alignment now look for the exit
  shade (`/mission/banner_target`), green outbound; orange is optional.
- Board identity: the border ring and outline depth follow the GCS border
  (1 in, 0.7% of the board's width, against the 3% ring sized for 3 in); a
  corridor-width board framed along both long sides passes with its ends
  dark at the walls (`WIDE_BOARD_ASPECT` 2.5); the border's white may be
  judged against the light the supplied print is in (`white_illum_ratio` 0.9;
  a #0000FF panel read V 193 beside a V 202 border), border test only.
- Return search height: at the entry banner's measured lineup height from
  the hung-board pass only, clamped to corridor..search altitude (it had
  flown at 1.5 m, the board's top out of a level camera's frame).
- Borderless QR: zbar retries on an Otsu-thresholded crop of a located code
  (on the grey-157 pad, 0 of 39 start frames decoded as they came, 39 of 39
  thresholded), which also gives the code's own corners; a start-marker
  reference is kept only when wholly in frame.
- Simulator: exit-coloured return boards; 1 in borders; QR printed without
  its quiet zone; ground board 1 ft; obstacle height from the GCS; laid
  sheets on the zone drawn on its slab (`scripts/materialize_world.py`);
  `scripts/field_pdf_world.py` builds `sim/worlds/aerothon26_field.json` and
  `aerothon26_field_L10.json`.

Evidence, laptop-simulation route, calm, inputs entered through the GCS
(`logs/field_pdf_20261025/`, receipt `.scratch/field_pdf_20261025/receipt.json`):
runs r1-r4 were stopped or skipped delivery and drove the fixes above
(`INTERRUPTED.txt` in each stopped run). On the final flight source, graded by
`sim/check_track.py`:

| Run | World, QR mode | Result | Flight | Drop / payload | Closest red / obstacle | Landed |
|---|---|---|---|---|---|---|
| r5 | 22 ft lanes, pad C, pattern only | 14/14 | 403.9 s | 0.24 / 0.27 m | 7.68 / 0.64 m | 0.11 m |
| r6 | 10 m lanes, pad A, pattern only | 14/14 | 419.9 s | 0.17 / 0.20 m | 1.57 / 0.62 m | 0.11 m |
| r7 | 22 ft lanes, pad C, payloads read | 14/14 | 390.8 s | 0.27 / 0.27 m | 7.30 / 0.68 m | 0.21 m |

Pattern only is `AEROTHON_QR_IGNORE_PAYLOADS=1` (the PDF's "scan the
pattern of the QR code"). The corridors were flown at 1.2 m: DuckUnderBoard's
first look is already under the 8 ft edge and drops its 0.6 m margin. The
winch drop (descent, lowering, release, retraction) took 151-177 s and the
search 33-70 s. Three calm simulated runs; field
conditions, gusts and the aircraft are not re-qualified on them. After r5-r7
only the GCS state names of the three SetBannerTarget leaves (they had read
IDLE) and the offline editor's preset export (validated presets, as the
aggregator serves them) changed; no decision logic.

Every GCS testing option was run in the same world, each started as the
operator's Start does, flight options from the take-off pad
(`logs/field_pdf_20261025/gcs_campaign/summary.json`): QR and SLAM (live
output, stopped), banner (green entry banner identified, square on -2.1 deg at
4.8 m), waypoint avoidance (through the entry corridor on its centreline at
1.5 m into the zone), transmitter avoidance (simulated sticks, operator stop),
mechanism lower and stow, deliver here (start QR, 0.20 m image offset) and GPS
delivery (pad C, 0.45 m image offset). The GPS delivery counts from its own
session: run after deliver here it flew with no payload and correctly refused
to confirm a drop.

**26 October, watched runs, red zone near the target pad.** After commit
`e5b7e07` the operator watched full runs with the Gazebo window open (pattern
only, pad C; r8 was started from the GCS Start button):

| Run | Red zone (world centre) | Result | Flight | Drop | Closest red | Landed |
|---|---|---|---|---|---|---|
| r8 | field world, (36.0, 4.0) | 14/14 | 387.9 s | 0.24 m | 7.65 m | 0.34 m |
| r9 | (15.0, -2.5), 4 m west of pad C | **9/14** | 308.0 s | 0.20 m | entered at 15 m | 0.10 m |
| r10 | (21.0, 2.0), 2 m north of pad C | 14/14 | 368.0 s | 0.20 m | 2.32 m | 0.07 m |

r9 (`sim/worlds/aerothon26_field_red_near_c.json`) confirmed the red zone
mid-search, re-planned round it four times and delivered 0.20 m from pad C,
then failed: the red square lies on the return lane's axis 4.8 m from its
mouth, so every return stand-off ReturnToCorridorMouth tries (3-5 m out, 2 m
either side, outside the 1.5 m clearance round the camera's red boxes) was
on red ground, and the mission refused "destination lies inside 1 confirmed
red zone". The FC then flew RTL at 15 m straight home over the red zone and
the corridor (red entry, return lane, ceiling, failsafe mode: 5 checks).
Fixed the same day (below). r10 (`aerothon26_field_red_by_c.json`) routed its search and
return round the same square beside pad C. r10 flew the calibration changes
below with no calibration saved (output = angle; `mavlink` winch in the
simulator), before the `execution_node` fix, which no full run has flown yet.

The same day: GCS Camera cal and Winch cal (section 6); `execution_node` now
publishes COMPLETED on `/mission/state` when a landed mission completes (it
recorded it without publishing, so the state stayed LAND: disarmed-only GCS
reviews and RC6 hand drive stayed locked until reconnect); disarmed in
Gazebo, the simulated airframe's rotors keep turning at about 18 rad/s with
rotor_3 against its controller's sign while the FC sends 1100 us (zero
command), so the model creeps counter-clockwise on the ground, about 0.6
deg/s of simulated time (simulator vehicle model only; the real aircraft's
props do not turn disarmed).

**Return gate with red ground in front of it (r11, r12).** r11 flew the r9
world again with `/percep/redzone/detail` recorded: the confirmed cells (19
m2 for the 9.3 m2 square), the detector's 1 m inflation, merging and the
1.5 m clearance made one keep-out x 15.5..24.5, y -9.5..0.5 (home-local),
reaching to 1.8 m of the return face at x 13.7. Every point AlignToBanner
can square up from (3.3 m and more out) lay on it, so no legal camera
alignment existed; no margin was reduced. Now, when every return stand-off
is on red, ReturnToCorridorMouth enters the lane from the clear strip at its
face: the face is the outbound gate plus the corridor length along the
lidar-measured gate axis, across by the lane spacing (the recorded exit is
2.3 m past it); the entry is the farthest point 1.2-2.5 m in front of it
kept 0.25 m off the keep-out, reached round the red zone at transit height,
facing down the lane. `ReturnGateBlocked` then skips the camera search and
alignment and logs "return gate NOT identified or aligned with the camera"
(the return-lap banner task is lost, not faked); the return DuckUnderBoard
widens its lidar sector to see both wall ends from that close
(atan((lane/2 + 0.5)/distance) + 3 deg), and measures the edge, gap and
clearance as always; GateAdvance and the corridor follow unchanged. With a
stand-off clear, nothing changes. Red up to the face still refuses.

r12, the r9 world on that source: entry (15.2, -4.5), 1.7 m out; sector +-56
deg; board edge measured, a 3.6 m gap, gate 1.42 m, advance 2.02 m; return
lane flown through, landed 0.07 m from home, delivery 0.17 m: **13/14**. The
failed check is a red-zone entry in the SEARCH at t = 174 s: the sweep's
first lane runs south over the square 4.4 m from where it starts, at the
simulator's fixed 5.56 m/s (`search_speed_override_mps`, which disables the
stop-short-of-red guarantee; red was confirmed a second too late). r9 passed
0.57 m from it and r11 1.69 m. The aircraft's `venue.yaml` sets no override:
its search is paced on the detectors.

Regressions (pattern only unless noted, graded by `sim/check_track.py`):

| Run | World | Source | Result | Flight | Drop | Closest red |
|---|---|---|---|---|---|---|
| r13 | field, 22 ft lanes | return fix | 14/14 | 344.0 s | 0.23 m | 7.66 m |
| r14 | field, 10 m lanes | return fix | 14/14 | 410.9 s | 0.22 m | 2.04 m |
| r15 | red beside pad C | return fix | 7/14, winch ACK | 236.5 s | 0.18 m | 2.48 m |
| r15b | red beside pad C | return fix | 14/14 | 346.9 s | 0.20 m | 2.48 m |
| r16 | r9 world, paced search | return fix | 6/14, winch ACK | 170.3 s | 0.18 m | entered in RTL |
| r16b | r9 world, paced search | final | 14/14 | 511.9 s | 0.18 m | 2.40 m |
| r17 | field, 22 ft lanes, payloads read | final | 14/14 | 356.9 s | 0.23 m | 7.95 m |

r15 and r16 failed on "flight controller refused DO_WINCH lower (result
0)": MAVROS stops waiting for the COMMAND_ACK with success false and result
0, ACCEPTED's code, and the FC reported lowering 45 ms after the fault (also
`logs/return_lap_20261020/final_mission_r14`). The mission failed and RTL
flew over the red zone and the corridor. `winch_ctrl` (mavlink backend) now
takes an unanswered lower or stow as accepted once the measured line moves
0.05 m its way within `unacked_motion_s` 3 s, a fault otherwise; with no
measured line it is still a refusal, and the aircraft's L298N sends no
DO_WINCH. In r16, paced on the detectors, the search was planned round the
red square from its start ("avoiding 4 red zone(s)"); its only entry was the
RTL's climb-out at 14.7 m. r16b, the r9 world paced as the aircraft flies, on
the final source: search round the square, return lane entered from its face
(1.5 m out, sector +-59 deg, gate 1.33 m), 14/14 in 511.9 s. r13-r15b flew
the source before the winch change, which only the unanswered-command path
uses.

### 29 October 2026: the field's markers are AprilTag 36h11, not QR

The operator photographed the venue's boards on 29 Oct: square black-bordered
fiducials on white boards, not the PDF's borderless QR codes. Every OpenCV
aruco dictionary was tried on the photographs: each board reads as
**AprilTag 36h11** (`DICT_APRILTAG_36h11`) with **IDs 100, 200, 300, 400 and
500**; the 4x4, 6x6 and original-ArUco hits were 16-42 px specks in the
background. ID 300 appears in two photographs at different places, possibly
the take-off copy of a pad (not confirmed). The tag is 8 x 8 cells, black
border included, on a white margin about one cell wide (a tenth of the board).
Crops of the six boards, marker only, are the fixture
`tests/perception/field_tags_20261029/` (`expected.json` gives the IDs).

What changed (perception and simulator; mission tree, planner and search
geometry unchanged):

- `perception_qr/tag_decode.py`: `TagDecoder` reads tags with OpenCV's aruco
  module (4.6's `detectMarkers` on the Pi's Ubuntu 24.04, `ArucoDetector` on
  4.7+) and keeps `QrDecoder`'s contract: the payload is the ID in decimal
  ("300"), quads are the tag's own corners. `minMarkerDistanceRate` is 0.02,
  not OpenCV's 0.05: a white board on darker ground thresholds to a dark band
  round the board, a candidate a margin larger than the tag, and the default
  kept the band and dropped the tag (48 of 224 flat-shaded synthetic boards
  from 24 to 360 px unread, as Gazebo renders them; 0 at 0.02; all six
  photographs read at either). Motion blur reads up to about a fifth of the
  tag's width. Ground textures (noise, paving) read as nothing. A tag seen
  but not identified is reported unread only when it shows a dark border
  ring; blurred past reading, a tag is not even a candidate, so the unread
  hold rarely applies to tags.
- `qr_node`: `marker_kind` 'aruco' (default) or 'qr'; `marker_dictionary`
  (default `DICT_APRILTAG_36h11`). With tags a pad matches when its ID equals
  the start marker's (`qr_match.same_tag`: "300" and an operator's "ID 300"
  are one tag, "30" and "3000" are not). QR appearance matching is off for
  tags (the ID is the pattern), so the mission's `APPEARANCE_ONLY` fallback,
  which needs a QR module grid, never stands in for an ID; `use_payloads`
  false no longer discards anything for tags. `/percep/qr/detail` carries
  `marker_kind` and `marker_dictionary`. Topic names keep "qr".
- Launch: `AEROTHON_MARKER_KIND` (default `aruco`; `qr` for QR codes) and
  `AEROTHON_MARKER_DICT` (default `DICT_APRILTAG_36h11`), read by
  `mission2.launch.py` like `AEROTHON_QR_IGNORE_PAYLOADS`. On the Pi they go
  in the launcher environment. `scripts/check_pi_runtime.sh` now checks that
  the aruco module has the 36h11 dictionary.
- GCS preset "AeroTHON 2026 Track 1 field (organiser PDF)": QR white border
  0.1 m (was 0), the photographed margin, with 1 m taken as the board. The
  board's real size and margin are still to be measured on the day; the
  plausibility gate (0.15-3.5 m) does not depend on them.
- Simulator: world specs carry `qr.kind` (`apriltag_36h11` by default, or
  `qr`) and `qr.ids` (pads a-e, default 100-500, distinct, 0-586); the start
  marker prints the target pad's ID. `scripts/materialize_world.py` prints
  the tag's cells (`materials/tag36h11_matrices.json`, from OpenCV's own
  dictionary by `scripts/generate_tag_matrices.py`) on a white plate, with
  the GCS QR border as the margin, or a tenth of the board when a world gives
  none. The four field worlds carry the tags and the 0.1 m border. Every
  world now prints tags unless it says `qr`, matching the aircraft default.
- Not changed: the sweep is still sized for a 33-module QR at 5.3 px per
  module (8 m for a 1 m marker on the 0.85 rad camera). A tag's 8 cells need
  far fewer pixels, so this is conservative; raising the sweep is a separate,
  flight-facing change. The headless world (`sim/headless_world.py`) still
  models QR reading at the object level.

Tests: `sim/test_tag_decode.py` (field photographs, rendered boards at every
size/turn/ground, blur, textures, node matching, world printing, a printed
board read from above, so not mirrored); QR-path tests now set
`marker_kind` qr.

Runs (laptop simulation through the world maker and the GCS, calm, graded by
`sim/check_track.py`, `logs/aruco_markers_20261029/`, receipt
`.scratch/aruco_markers_20261029/receipt.json`): in progress.

### 30 October 2026: the surveyed venue

The operator measured the venue and surveyed it with GPS about the take-off
pad (home 13.1705900, 77.5331760). Their figures override the field PDF
(whose SHA-256 is unchanged) where they differ:

- Markers: AprilTag 36h11 only. The ten photographs in `actual markers/`
  read as IDs 100, 200, 300 (two boards), 400 and 500. The first marker can be
  any of them; the aircraft finds its match in the delivery zone as before.
- Corridors: 6 m long, 3.5 m (11.5 ft, the banners' width) wide, walls 3 m;
  a 1.5-2 m gap between them; banners as the PDF. The exit lane holds two
  boards, 2 m tall, at most 1.5 m from the wall, 4-5 cm thick; the entry lane
  none.
- Take-off: a red pad of about 0.5 m, the aircraft on it at take-off and
  landing, the first marker about 1 m in front. One red zone, 3 x 3 m.
- Organiser points: two fence points behind take-off (left and right) and the
  delivery zone's four corners. Search only inside the corners; the fence is
  all six.

Survey, in the corridor frame (the lanes run 286.5 deg true): lanes 6.1 and
6.3 m long, 2.25 m apart, mouths 5.2-5.7 m in front of home; the zone 17.8 x
23.9 m from 12.2-13.4 m in front, square to the lanes within 3 deg, its
corners up to 1.2 m off a rectangle. The back-right point is 5.4 m behind and
23.4 m right of home ("really wide on the back side"); the back-left point as
typed lay 122 m ahead, so the worlds mirror the back-right one. Another team's
points put the zone about 3 m left and their entry lane 2.8 m long; they are
not used.

What changed (decision code, authorised by the operator; section 4 "The
venue's six points"): a turned four-corner zone, refused before as "not an
axis-aligned ENU rectangle", is searched as its polygon, lanes trimmed 1 m
inside it and 3 m inside the arena fence; red ground counts only where it
touches the zone, so the red take-off pad is not a keep-out; readiness accepts
turned corners. GCS: a delivery-zone corners box, Apply geofence sends the
outline of all six points, Apply delivery zone the corners; built-in preset
**AeroTHON 2026 venue (30 Oct survey)** (lanes 6 x 11.5 ft x 3 m, spacing
11.5 ft + 2 m, navigation 1.5 m, red zone 3 m, boards 2 m reaching 1.5 m,
1 m markers with 0.1 m margin).

Simulator: world specs take a turned zone (`delivery_zone.yaw_deg`), a venue
take-off pad (`takeoff.pad_m`, `pad_colour`, aircraft on its centre) with the
start marker `start_marker_ahead_m` in front, and a fence of points behind
take-off plus the zone corners (`geofence.mode` "behind"). `scripts/venue_world.py`
builds the surveyed venue in the corridor frame and turns it to 163.48 deg
ENU about home, so the GCS receives corners turned as the organisers' will be:
`sim/worlds/aerothon26_venue.json` (boards 1.5 m, first on the left flying
home, 2 m gap, red zone mid-left, target C), `aerothon26_venue_far.json`
(boards 1.5 m, first right, 1.5 m gap, red zone before the exit, target B in
the far corner) and `aerothon26_venue_r10.json` (boards 1.0 m, target D).
Working values to confirm on the day: boards at 2 m and 4 m along the lane,
start marker centre 1.5 m in front of the pad centre, pads and red zone placed
by the world, not known. The organiser inputs endpoint gives the two back
points, the four corners and their outline; the headless world sees the red
pad as red ground.

Evidence (`logs/venue_20261030/`, receipt `.scratch/venue_20261030/receipt.json`):
in progress.

### 30-31 October 2026: organiser points at the GCS, venue runs

The operator asked for the GCS to take the aircraft to each organiser point
and record it: the six fence points first (required), then home and the two
corridors' ends (optional, as before when absent). Section 4, "Organiser
points", has the panel, recording and what the mission does with the course
points (guidance only: face the entry corridor, refuse a gate in the exit
lane, return to the recorded exit mouth, return home, advisory home check).

Changes the runs drove (flight logic):

- `Corridor`: hold position where the walls end. Switching the navigator off
  sent nothing; the FC flew its last velocity until its setpoint timeout and
  coasted 1.4 m after the exit (headless c04/c07/c09 climbed over a red
  square 3.7 m past the entry lane's exit). Now it stops 0.2 m on.
- `AlignToBanner`: a heading's dwell waits for frames (min_samples, up to 3
  dwells). The detector drops frames while the camera turns to its pose; in
  rendered runs the sweep's first heading, after a pose change, closed at
  0/0 frames. With no course points that was the one heading facing the entry
  banner (GUI run 2): the board was never read and the recovery flew along
  the exit lane at gate height into its first board (FC crash disarm). Run 3,
  aborted from the GCS at 1361 s, never read it either.
- Tried and reverted (`7031bd7`): leaving red ground's margin sideways rather
  than back over the corridors. The router's segment certificate allows only
  the nearest-edge escape; the aircraft then held over the margin until the
  search deadline and RTL.

Headless grid (object-level, navigation only: delivery not exercised; RTF 1,
two at a time, `logs/venue_20261030/headless_course/` with course points,
`headless_g/` without, `headless_final_nocourse_pre_escape/` without, source
identical to the merge): every board case flew both lanes -- reach 1.0, 1.25
and 1.5 m, first board either side, 1.5 and 2 m gaps -- with corridor
clearance 0.79-1.02 m and red clearance 2.4-4.8 m, landing 0.6-0.72 m from
take-off. With course points: faced the entry mouth, accepted the gate (0.6-0.8
m from the recorded mouth), returned to the recorded exit mouth (2.0-2.2 m from
the derived one); one world's flight 230 s against 416 s without. The three
worlds with a red square 3.7 m past the entry lane's exit fail two checks
with or without course points: red clearance 1.06-1.25 m (no entry) and the
search's escape from its margin crossing the corridors' ends at 10 m. A red
zone that close to an exit is the open limitation. Earlier batches with three
runs at RTF 2 starved the corridor controller (setpoints at ~2 Hz); their
results are not evidence (`headless_b/INTERRUPTED.txt`). The headless grid
predates the dwell change, which only acts on frame-starved dwells.

### 31 October 2026: skip-corridor mission, actuator start waiver

The operator asked for a second mission beside the full one. GCS Mission
panel: "Full mission" or "Mission, skip corridor" (runtime task
`mission_skip_corridor`, `build_root(skip_corridor=True)`). The skip mission
keeps take-off, the start QR, the search, the drop and the precision landing;
it replaces both corridor legs. After the start QR it climbs to
`skip_corridor_alt` (10 m), flies over the entry corridor's recorded ends
(`HighTransit`, GCS course points; without them it goes straight on) and
enters the delivery zone at 10 m (`EnterDeliveryZone`), then searches as
usual. After the drop it climbs to 10 m, restores the navigation speed, flies
over the exit corridor's recorded ends, goes home at 10 m, descends to the
landing's start height and lands on the pad. No banner alignment and no
corridor flight, so the rulebook's corridor and banner tasks are not flown.
Legs are routed round red ground already mapped; the camera stays nadir.
Standalone simulation selects it with `AEROTHON_SKIP_CORRIDOR=1`.

It first commands the navigation speed (`SkipTransitSpeed`): the full
mission's gate crossing does that, the return restores it after the search's
cap, and without it the first headless runs failed the return "pre-search
navigation speed unavailable" (`logs/pi_deploy_20261031/skip_headless_run1_no_speed`).
Headless after the fix (navigation only, calm, RTF 1,
`skip_headless_run2/`): venue c01 with course points, 122 s, red clearance
1.74 m; c06 with the fence only, 176 s, red clearance 2.99 m; both no red
entry, no fence exit, no unexpected mode, landed 0.6 m from take-off, maximum
10.06 m. Their failed checks are the three corridor checks (by design) and
the two payload checks this harness does not exercise. Not flown rendered or
on the aircraft.

Start waiver (operator, 31 Oct): on the aircraft the tilt servo reports no
motion and the L298N winch has no encoder, so `camera_actuator` and
`winch_actuator` are never ok and every mission Start was refused. The local
execution watchdog now marks both `waived_for` the two mission tasks (the
winch only while it reports no fault); they stay not-ok and still block the
other flight tasks. Check the servo and winch by hand before Start. The
simulator's gateway reports measured actuators and is unchanged.

Timed drop (operator, 31 Oct). The aircraft has no loaded/unloaded hover
calibration (profile `delivery_calibration` empty), and the delivery observer
refuses at once ("load calibration missing or unqualified"): the mission
failed into an FC recovery at the pad with the payload on the hook. Without a
calibration `WinchDrop` now lowers to the release height plus 0.5 m of slack
(or the line's limit, at most 40 s), holds 5 s stopped for the gravity hook,
winds the line up (at most 45 s, else a failure) and records the delivery as
unconfirmed; the mission then flies its return. A winch fault, or winch status
stale for 3 s, fails the drop as before. A calibrated aircraft keeps the
observer. Unit-tested (`sim/test_timed_drop.py`); the line lengths are the
l298n estimate (0.30 m/s), not measured travel.

The camera runs at 15 Hz (`mission2.launch.py`): at 30 Hz the Pi's CPU was
saturated (load ~20) and the detectors and runtime received ~0.4 frames/s. The
FC's TELEM3 port was MAVLink 1 (`SERIAL5_PROTOCOL 1`), which refuses fence
uploads ("Need mavlink2 for item transfer") so every Start stopped in
PREFLIGHT; it is now 2 (set through MAVROS, FC rebooted).

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
`/mavros/local_position/velocity_local`, `/scan_driver`, `/scan_raw`, `/scan`, `/image_raw`,
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

The venue's markers are AprilTag 36h11 tags (section 1, "29 October 2026"),
read by default (`marker_kind` aruco): the tag ID is the payload and the
pattern, and a pad matches when its ID is the start marker's. The rest of
this section is the QR path (`AEROTHON_MARKER_KIND=qr`).

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
`AEROTHON_REQUIRE_ARENA_DIMENSIONS=0` and the item reads WAIVED. The 23
fields cover corridor, hall, banner (including the ground board's own
height), QR, red zone, payload and the exit-corridor obstacles' reach
(fraction of corridor width) and height. A navigation height that puts the
lidar plane (0.0815 m over the body) less than 0.1 m under the obstacle tops
is refused with the largest acceptable height named: the aircraft would fly
the corridor without seeing them. Built-in preset **AeroTHON 2026 Track 1
field (organiser PDF)** holds the 23 Oct field PDF's values (section 1).
Fields marked "rec." are recorded for the operator only. Input
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
gateway). The header shows
the active profile and vehicle kind. Flight operations and Testing work with
either vehicle. Connections saves vehicle profiles on the Pi:
FCU TCP/UDP/UART, hostname, ports, system/component identity, remote sensor
gateway, local devices, calibration and RC mappings. Save only with runtime
stopped and aircraft disarmed. The selected real-drone profile connects
automatically at boot, without a props checkbox. Connect prepares sensors and the supervisor;
it does not arm, start a mission or move the camera. A profile with SLAM enabled
starts production mapping; the GCS displays its frame, origin and timestamp.
The native UART router starts independently before networking and Docker. It
uses the measured UART in runtime.env before any profile has been saved, then
follows the selected serial/network profile. Mission Planner listens on UDP
14550; the router discovers LAN interfaces every second and broadcasts telemetry
as soon as the FC and operator network are available. Pi/FC boot and Wi-Fi
association still take time after battery connection. Connection starts no mission.
Outbound GCS telemetry coalesces bytewise UART reads for at most 10 ms into
datagrams no larger than 1200 bytes. Previously each tiny read became another
Wi-Fi broadcast, congesting the LAN during full telemetry. Local MAVROS data
and inbound FC commands remain immediate. Learned UDP peers expire after 30 s
without traffic; configured targets and LAN broadcast remain available.
The router also announces the Pi in Mission Planner's Messages tab (29 Oct
2026): `Pi booted N s ago` once the FC link first carries data, and `Pi Wi-Fi
up: <network> <address>` each time a Wi-Fi interface gets an address, as
MAVLink 2 STATUSTEXT (INFO) from the FC's system id as the onboard computer;
Mission Planner shows them as `191 : ...`. Each goes to the FC, which forwards
it to a Mission Planner on USB, and to the Wi-Fi GCS endpoints; a GCS that
connects over Wi-Fi later is sent the latest of each. Not through ExpressLRS:
`MAV2_OPTIONS 2` stops forwarding to that port. Serial FC only; `--no-announce`
turns it off.
An explicit Disconnect pauses automatic runtime connection until the next
Pi/web-host restart or an explicit Connect. A profile can opt out of automatic
connection; simulation profiles opt out by default.

For real hardware the default mapping pose source is LiDAR scan matching,
independent of GPS and the FCU local-position stream. Its TF tree is
`map -> lidar_odom -> lidar_mapping_base -> lidar_mapping_scan`; its scan topic
is `/scan_slam`. This tree does not supply flight-navigation pose or change the
FCU's `odom -> base_link` transform. Insufficient returns, degenerate scenes,
poor overlap or failed registration hold new map updates. The alignment gate
scales with each reference scan's measured scatter about its wall lines:
40-80 mm in tracking (20-40 mm when revalidating), so the C1's own ~20 mm
scatter is not mistaken for misalignment. When the keyframe stops registering,
the previous accepted scan continues tracking and becomes the new keyframe.
While held, each raw scan registers against the newest registered held scan,
or the previous scan carried at constant velocity, to dead-reckon an
unpublished prediction. That prediction seeds and bounds re-registration
against the keyframe. A chain with at most one constant-velocity scan may
also resume tracking directly. Both paths keep the 2 m/s and 90 deg/s average
bound since the last accepted pose. A capture gap, more than one second
without a registered scan or 1 m of accumulated uncertainty drops the
prediction. Mapping then resumes only after tightly matching the previous
scene with small motion; larger uncertainty requires a new mapping origin.
FCU mapping remains selectable for qualified GPS/EKF operation and
is the simulation default. The GCS shows mapping state, a full-resolution live
scan independent of map availability, metric axes and scale, zoom and pan.
Map cells retain native resolution up to 1024 cells per side; larger display
grids declare their coarser resolution. All 720 C1 beams are retained in the
live view. Unknown cells remain unknown.
Each browser has a bounded output writer: pending maps and telemetry retain
their latest snapshots, while command receipts retain order. A map transfer
can no longer silently remove the browser after the former 100 ms write limit;
a genuinely stalled connection closes explicitly so the browser can reconnect.
Map runs use lossless encoding, preserving every native cell rather than
thickening walls to save bandwidth. Deflate-capable browsers receive the normal
telemetry stream; an uncompressed proxy/client is paced to two display snapshots
per second. Mapping and avoidance still consume the original sensor stream.
Built JavaScript/CSS include precompressed gzip assets so the Pi can serve
the browser over the LAN with fewer transferred bytes.
The pinned slam_toolbox 2.8.5 occupancy raster rounds maximum endpoint indices
to its width/height and then drops them as outside the array. The local
`aerothon_slam_grid` adapter adds the required last row/column when rastering
the existing optimized scans. It is compiled for the destination architecture,
checks the exact upstream version at build time and is preloaded only into the
SLAM node. It leaves upstream binaries, scan matching, flight pose and clearance
checks intact. One traversing ray marks observed free cells for the display
mapper; the resulting occupancy map is not a flight-clearance input.
Camera view tabs do not move the camera; explicit camera tilt is reviewed.
Before flight, enter the banner and red-zone shades as `#RRGGBB` in Organiser
inputs, then review Apply colours while disarmed. Roles
(`perception_banner/colours.py`): **Entry corridor banner** (green, flown to
on the outbound lap), **Exit corridor banner** (the return lap's banner; the
field PDF's blue `#0000FF`), **No-entry banner** (the earlier rulebook
reading's orange at openings not to take; blank when there is none) and
**Red zone**. Green and red are required, and one of exit or orange. With an
exit shade the mission tells the detector which lap it is on
(`/mission/banner_target`: green outbound, exit from the return search to the
end of the return corridor); without one the return lap looks for green.
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

**Organiser points: the six fence points first, then optional course points
(30-31 Oct 2026).** The organisers give two fence points behind the take-off
pad and the delivery zone's four corners; the aircraft searches only inside
the corners, and the fence is all six. Organiser inputs lists one slot per
point in priority order: the six fence points (required: behind take-off
left and right, zone corners 1-4 in any order), then home and the corridors'
ends (optional: entry corridor home-side and zone-side mouths, exit corridor
zone-side and home-side mouths). Each slot takes a typed `lat, lon` (Set), or
**Record here**: take the aircraft to the spot (carried or flown) and the
aggregator averages its own GPS for 5 s, refusing without a 3D fix, with
fewer than 8 satellites or with fixes spread over 2.5 m
(`gcs_aggregator/organiser_points.py`). "Fill fence points" takes six pasted
lines. Points persist in `~/.aerothon/organiser_points.json`. **Apply
organiser points** (disarmed) sends the fence as the outline (convex hull)
of the six, the zone as the four corners, and the course points on
`/mission/course_points`; a corridor counts only with both its ends.

The course points are guidance; the camera and lidar still find, square up
on and fly every gate, and without them nothing changes. Recorded entry
mouth: the aircraft turns to it before the outbound banner search
(`FaceEntryCorridor`), and a gate the points place in the exit lane is
refused and searched for once more, failing the mission on a second refusal
(`CheckGateAgainstCourse`: over 3 m from the entry mouth and 2 m nearer the
exit lane's, or over 4.5 m with no exit lane recorded). Recorded exit lane:
the return flies to its zone-side mouth when that is within 6 m of the mouth
derived from the outbound gate, keeping the lidar-squared axis. Recorded
home: GotoHome flies there when it is within 5 m of the FC's home, and
readiness shows an advisory "Home point" item (aircraft within 2 m of it;
"Check", never a hold). Recording with the aircraft's own GPS keeps the
points consistent with the FC's estimate. A zone square to north is
searched as its rectangle as before; one turned to the ground (the venue's
runs 16.5 deg off east-west) is accepted as a convex quadrilateral
(`boundary_to_local_polygon`) and searched like the judges' polygon: lanes
over its bounding box trimmed 1 m inside it, and also 3 m inside the arena
fence (`Mav.search_fence`), because its far corners are fence vertices and
the FC's 2 m FENCE_MARGIN would brake a lane 1 m inside the zone. Red ground
is kept only where it touches the zone (`inside_delivery_zone`): the red
take-off pad is not a restricted zone. Readiness "Search area" reads
"supplied corners (turned polygon)". Built-in preset: **AeroTHON 2026 venue
(30 Oct survey)** (section 1, "30 October 2026").

**Without zone corners the judges' geofence is the one organiser polygon.**
Paste the points into the geofence box alone, one `latitude, longitude` per
line: the GCS counts them, draws the draft dashed on the Map tab, and after
Apply geofence draws the applied polygon filled. The rulebook says "Delivery
zone geo-fence coordinates will be provided"; the team expected a fence round
the whole flying area. Take-off decides which
(`delivery_zone.judges_polygon_role`), on the aircraft and in readiness alike:

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

The ZIP contains 13 local flight/GCS ROS packages, selected operating scripts,
built `gcs/` assets with offline satellite tiles, these two guides and a SHA256
`runtime_manifest.json`. It excludes simulator packages/models, tests, evidence,
developer tools, CAD, Node/Rust dependencies, build/install outputs and caches.
It refuses an existing ZIP. Build ROS output on the destination architecture.
External drivers and OS dependencies are not application source.

Regional offline imagery is not in the ZIP. `scripts/map_regions.json` lists
the cached regions (18 October: VIT Vellore, zoom 0-19, 4,104 tiles); the
GCS draws each as a bounded layer above the bundled simulator tiles, overscaling
a region past its maxzoom. Fetch on an internet-connected host, then copy into
the web host's tile cache, which `/satellite/` reads after the bundled tiles:

```bash
python scripts/download_map_tiles.py --out <tiles-dir>
tar -C <tiles-dir> -cf - . | ssh pi5@<pi> 'mkdir -p ~/.local/state/aerothon/map-tiles && tar -C ~/.local/state/aerothon/map-tiles -xf -'
```

Re-running the download resumes. Imagery is Esri World Imagery; its terms of
use govern bulk download, so keep regions to the sites actually flown.
After editing the regions, rerun `scripts/export_gcs_contract.py` and rebuild
the GCS so its declared coverage matches the cache.

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
geoid data. Add reviewed upstream lidar driver source to the workspace and
record its revision; external drivers are not in the application ZIP. Match
the driver to the actual fitted lidar. The fitted unit is a Slamtec RPLIDAR C1
(CP2102N USB, 460800 baud): `sllidar_ros2`, selected by `lidar_model:=c1`
(the default). Unlike the LD06, the C1 spins only after its driver sends the
start-scan command, so a stopped C1 indicates a wrong or absent driver, not
missing power. `lidar_model:=ld06` keeps `ldlidar_stl_ros2`.

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

The destination is `pi5`, Debian 13 arm64 on a Pi 5 with 8 GB RAM. On 19 October
2026 its measured addresses are Ethernet `192.168.0.104` and Wi-Fi
`192.168.0.103`; the earlier `192.168.0.101` address was a previous DHCP lease.
Use the Ubuntu 24.04/Jazzy container route on this OS. Installing Ubuntu ROS
APT packages directly into Debian would mix distributions. The pinned official
ROS base image and dependency recipe are in `scripts/pi_runtime/Dockerfile.dependencies`.
Build that as `aerothon-dependencies:20261014`, then build
`scripts/pi_runtime/Dockerfile` as `aerothon-runtime:20261014`. The final stage
uses the completed dependency image directly and clears installation proxy settings.
Build dependencies inside that environment; Node, Rust, Gazebo and SITL stay
off the Pi. The external C1 driver is `Slamtec/sllidar_ros2` at revision
`34300099fadfc772965962dec837bf436706188f` in
`/home/pi5/aerothon_ws/src/sllidar_ros2` (16 October 2026: `/scan_raw`
10.0 Hz, 720 beams, health OK on the Pi). The alternative LD06 driver is pinned
to upstream revision `bf668a89baf722a787dadc442860dcbf33a82f5a`, with its own inventory.
Apply `scripts/pi_runtime/ldlidar-pthread.patch` in the LD06 driver directory before
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
It connects the selected automatic profile at boot with no vehicle execution.
`aerothon-router.service` starts after local filesystems, before networking
and Docker, and is the single UART owner. No GCS Connect or props checkbox
is needed for routing. It uses runtime.env until a profile selects a link.
Network profiles use MAVROS directly through their configured TCP/UDP endpoint;
they do not open the physical UART. The former console service is disabled,
and direct mission-service launch refuses to create a second controller.

The web process is supervised inside a persistent container. A web-process
restart can adopt its existing ROS child by boot/PID identity. Service shutdown
first requests safe runtime disconnect; it refuses termination of a controlled
runtime without live disarm. The Docker attach process uses `--sig-proxy=false`
so a refused stop does not forward a kill to the flight container. Power loss
and FCU failsafe remain separate hardware concerns.

Open `http://192.168.0.104:8899/` or `http://192.168.0.103:8899/` and run Connection check. The existing
drone profile connects automatically; Connections configures another profile
when required. The measured TELEM3 link is `/dev/ttyAMA2` at 115200,
BCM4 TX/header7 and BCM5 RX/header29. `/dev/serial0` is the debug/login UART.
For laptop simulation, use its gateway endpoints instead. Supply organiser
arena dimensions, the judges' geofence and banner colours through the GCS,
inspect readiness, then Review start and Confirm Start.

19 October 2026 deployment: the SLAM UI runtime ZIP with SHA256
`018ae196716af83dc3624aad8adf417655b6e373ceb3749d87bb446a2f139156`
was installed with all 265 manifest files verified. A fresh native ARM64
build completed all 15 workspace packages. The active `install` symlink
selects `install_20261019`; the previous install remains at
`install_before_20261019`. Both destination services are active and enabled.
The browser loads `index-BvJeOAWo.js`, and both network addresses delivered
fresh, disarmed FCU telemetry over WebSocket. No lidar scans or camera device
were present during this check, so live SLAM and camera operation remain
unverified on this deployment.

Wi-Fi was restored with a root-private persistent NetworkManager profile
for `iphone`, with autoconnect enabled and Ethernet preferred. Local gateway
and GCS access succeeded over Wi-Fi. Public IP and DNS probes failed through
the upstream network; NTP is enabled but has not synchronized. The Pi clock
was corrected from the operator computer while the runtime was stopped.
A final check failed on the absent optional `hwclock` utility after stopping
the GCS. The GCS was restarted and verified in the browser with live FCU
telemetry. No reboot occurred, and Wi-Fi persistence across reboot remains
unverified. Runtime/network backups are under
`/home/pi5/aerothon-backups/20261019-slam-ui/`; local deployment receipts and
the service recovery record are under `.scratch/pi_deploy_20261019/`.

Later on 19 October, a subscriber-only observation during the user's manual
POSHOLD flight confirmed persistent mapping loss. In 35 seconds the observer
received 339 raw scans at 10.01 Hz and 341 fresh mapping statuses, all Held
with `insufficient overlap`; it received no `/scan_slam` messages. Capture
intervals stayed below 0.129 s. The old grid continued to be republished, so
grid-message frequency was not evidence of accepted mapping scans.
The deployed mapper source hashes matched the local replay source. Replaying
these real scans from a fresh local origin accepted 46 scans, then remained
held for the final 24.48 s. Meanwhile 170 later adjacent scan pairs passed
the unchanged registration checks. The replay retained reference scan 46;
alignment failures aged that reference and triggered the stricter recovery
gate. This reproduces initialization followed by persistent loss of tracking
and supports investigating reference maintenance/recovery. The first rejection
of the actual flight preceded the capture, so its original trigger remains
unconfirmed. No runtime restart, parameter change, flight command or deployed
source change was made for this observation. It does not qualify mapping for
flight navigation; current avoidance still consumes `/scan` and FCU pose
independently. Evidence and the intentionally failing diagnostic replay are
under `.scratch/pi_deploy_20261019/held_*` and `replay_held.py`.

A local diagnosis of the 19 October manual POSHOLD capture, in which mapping
initialised and then stayed held, found two causes. First, the C1's
scatter about wall lines is ~20 mm, so even adjacent-pair RMS alignment error
had a 37 mm median. The fixed 40 mm tracking gate rejected 38% of adjacent
pairs, and the 20 mm recovery gate could never pass. Second, the aircraft was
not stationary: FCU local position recorded ~1.4 m forward drift at up to
0.86 m/s around capture seconds 10-12, with pitch between +3 and -6 deg.
Chained LiDAR registrations agreed with that displacement within ~0.1 m at
the time and ~0.2 m by the end. Once held, the mapper retried a stale seed
against a keyframe the aircraft had left. Recovery also required the pose to
lie within 0.15 m of the last accepted pose, so it never re-acquired. The
mapper now uses the noise-scaled gates and held dead reckoning described in
the mapping-pose paragraph above. Replaying the full capture tracks 332/339
scans: six consecutive scans are held during the drift and one later scan
is held alone. The original code tracks 46/339 and then stays held. Across 30 replays with 5 mm
range jitter and five start points, none ended held, the longest hold was
eight scans and at least 97% of scans tracked; the original ended held in
all 30. Registration costs 3 ms median and 21 ms maximum per scan on the
development laptop. Attitude-induced 2D scan bias remains: accepted poses
differ from FCU local position by up to 0.72 m (0.43 m RMS) in this capture, for
`slam_toolbox` to correct. A 90-scan slice of this capture is the regression
fixture `sim/fixtures/lidar_held_poshold_drift_20261019.json`. This is a
mapping-only change; it has not yet been deployed to or flown on the Pi.

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
**Measured link since 30 Oct 2026: TELEM3 on the Pi's UART2, `/dev/ttyAMA2`
at 115200**: TELEM3 pin 2 (TX) to header 29 (GPIO5, RXD2), pin 3 (RX) to
header 7 (GPIO4, TXD2), pin 6 (GND) to a Pi ground, pin 1 (5 V) unconnected;
`dtoverlay=uart2-pi5` with `dtparam=uart0=on` commented out, `runtime.env`
and the drone profile on `/dev/ttyAMA2`. That night Mission Planner stuck at
"Getting params" and the camera servo did not move: the FC's own
`@SYS/uarts.txt` showed TELEM3 (SERIAL5) RX at 0 bytes while it transmitted,
and GPIO14 (header 8) read 0 with its pull-up even with its wire removed, so
the UART0 TX pin is unusable (it failed a drive test on 16 Oct too). On UART2
the FC answered parameters and commands at once, and output 5 held the Pi's
poses (receipt `.scratch/fc_uplink_20261030/`). Two wiring faults on the way
look alike from Mission Planner: no common ground garbles FC -> Pi (97% bad
bytes at the right baud), and TX/RX swapped leaves the Pi's RX floating. From
23 to 30 Oct the link used UART0, `/dev/ttyAMA0`, GPIO14 TX and GPIO15 RX.
That destination setting takes precedence over
the proposal until a deliberate FC link change is measured. `/dev/serial0`
currently names the Pi debug UART `/dev/ttyAMA10` and its login console.
In the documented topology the router owns the serial device:

```bash
python3 scripts/mav_router.py --fcu-serial /dev/ttyAMA2 --fcu-baud 115200 \
  --mavros-port 14555 --gcs-port 14550 --gcs-broadcast \
  [--gcs-host <extra-laptop-ip> --gcs-out-port 14550]
```

MAVROS uses `udp://127.0.0.1:14555@127.0.0.1:14556`. Direct serial MAVROS
requires the router to release that device. Never share the physical UART.
The profile router passes `--gcs-broadcast` unless the profile sets
`gcs_broadcast: false`: FC MAVLink goes to each operator LAN's broadcast
address on UDP 14550 (docker/virtual links excluded, refreshed every 10 s), so
any Mission Planner in UDP mode receives it without an IP. The router drops
its own broadcast echo before the UART and skips unicast to a listener the
broadcast already reaches. Mission Planner UDPCl to `<pi-ip>:14550` also
works. Every LAN host can then read telemetry and send commands, so keep
the operator network isolated. The optional profile `gcs_host` (GCS
Connections, "Extra Mission Planner IP") adds one unicast target.

The user identified the FC as CUAV X7+ and confirmed ArduPilot **SERVO9** for
camera tilt. Confirm its physical output connector; this does not mean AUX9.
The file assigns `SERVO9_FUNCTION 7`, `MNT1_TYPE 1`, MAVLink targeting and
-90 to +30 degree pitch limits. Measure PWM endpoints, direction, supply,
angles and travel before use.

Camera poses are FORWARD 0, NADIR -90, ALIGN -45, BANNER -20 and GROUND -35
degrees. Fresh mount attitude is preferred. `readback=timed` assumes the
requested angle after the delay; it proves neither movement nor FC command
acceptance. Observe each pose and measure worst-move settlement.

The tilt servo is on SERVO5 (MAIN OUT 5) and **the Pi sets its pulse width
itself** with `MAV_CMD_DO_SET_SERVO` (27 Oct 2026; `camera_ctrl`
`fc_output: servo` in `venue.yaml`), with no mount (`aerothon_hardware.parm`).
Two FC set-ups failed on the aircraft first: `SERVO5_FUNCTION 56` (RC6
passthrough) took the output back from the Pi whenever RC6, the winch switch,
moved, and `MNT1_TYPE 0` refused every mount command (result 4); then a servo
mount (`MNT1_TYPE 1`) compensated an attitude the FC read as 31 deg nose-up
on the bench and squeezed forward / 45 / down into 1529 / 1202 / 1100 us.
Driving the pulse directly keeps the FC's lean compensation and level
calibration out of the camera.

**Only the Pi drives output 5; channel 8 tilts the camera through it, and
channel 6 only drives the winch** (operator, 29 Oct 2026). The FC leaves
output 5 free (`SERVO5_FUNCTION 0`, `MNT1_TYPE 0`). `camera_ctrl` passes
`rc_tilt_channel` 8 to the servo, as a pulse width, whenever no mission runs,
once the switch has moved since the Pi last commanded the camera (a Camera
cal pose or the end of a mission is not undone by a switch left where it
was). During a mission the receiver is ignored and the Pi's poses hold.
Two set-ups collided on 29 Oct: the Pi passed channel 6 to the servo, so the
winch switch tilted the camera, and `SERVO5_FUNCTION 58` (RC8 passthrough on
the FC) took the servo back from the Pi whenever channel 8 moved. ArduPilot
keeps a `DO_SET_SERVO` pulse on a passthrough output only until that channel
moves past its dead zone (`SRV_Channel::output_ch`,
`ignore_small_rcin_changes`). With output 5 free, poses through `camera_ctrl`
held on output 5 for 3 s each at 1590, 1000 and 2050 us.

Uncalibrated, forward is 1500 us and each degree down 5.56 us less (straight
down 1000 us), within `servo_pwm_min..max` (800..2200 us). **GCS Camera cal**
records the real pulse widths, disarmed:

1. Send Forward, 45 degrees down or Straight down. The aircraft sends what it
   believes that pose is (through the calibration in force, if any).
2. Look at the camera itself and nudge the output (-50/-10/+10/+50 us) until
   it is exactly at one of the three poses.
3. Press "This is ..." for the pose it is really at; the pulse width sent is
   recorded for that pose. Repeat until all three are recorded.
4. Apply, then Confirm in the dialog that opens over the window, which names
   the three outputs. (Until 29 October the confirmation opened in the
   Mission panel with the window closed; the operator never saw it and the
   recorded calibration never left the GCS, 28 October. Every calibration
   window's reviewed command now confirms over it, and command results show
   over it.) `camera_ctrl` (`tilt_calibration.py`) saves the three points, in
   us, to `camera_tilt.json` in the measured-state directory and sends every
   angle through them: each pose gets its recorded output, the others
   (banner -20, ground -35) the straight line through the neighbouring
   poses. The outputs must run one way from down to forward (a reversed servo
   is accepted); two poses within 10 us, or outside the pulse range, are
   refused; a calibration recorded in mount degrees is ignored. A pose out of
   reach needs `servo_pwm_min/max` widened. `/camera/pose_state` reports
   `output`, `output_unit` and the range. Clear saved returns to the
   uncalibrated line.

The simulator keeps the SITL mount (`fc_output: mount`, degrees, the joint
read back). Software-tested (`sim/test_gcs_calibrations.py`); not yet
performed on the aircraft.

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

### L298N payload motor, RC6 hand drive and winch limits

The aircraft flies `winch_ctrl` backend `l298n` (`winch_ctrl/l298n.py`,
bench-tested 24-25 Oct): the Pi drives ENA/IN1/IN2 (channel B: ENB/IN3/IN4 on
header 12/16/18; `l298n_lower_direction -1`, lowering on IN4). There is no
encoder: line out is motor run time times the line speed.

RC channel 6, a three-position switch, drives the motor by hand (high one
way, low the other, middle stop) only while no mission runs; channel 5 on
this transmitter has two positions and no stop. After startup, a mission or
a lost radio the switch must be seen in the middle before it drives at all
(25 Oct: a switch left at an end lowered the line at boot). The channels
reach the Pi from the FC (`RC_CHANNELS`, requested at 10 Hz; 5 Hz until
29 Oct). Silent past `rc_timeout_s` (0.5 s), hand drive pauses; it drives on
when they return with the switch still held. Only silence past `rc_loss_s`
(2 s) or a failsafe value counts as a lost radio (29 Oct: one gap stopped
the motor with RC6 held until the switch went back to the middle). Each
change is logged as `hand drive ...` and reported as `rc_manual_reason` in
`/winch/status`. **During an
autonomous mission the switch is ignored completely; fly with it in the
middle**, so it neither drives the motor before Start nor waits for the
middle again afterwards. On the FC channel 6 must do nothing: `RC6_OPTION 0`,
`TUNE 0`, `FLTMODE_CH` not 6.

**GCS Winch cal** (26 Oct 2026) sets where the line stops, on the props-off
bench, disarmed:

1. Start calibration. For up to 10 minutes RC6 hand drive ignores the limits.
2. Wind the line in with RC6 to where it should stop, switch to the middle,
   Set wound-up limit here (line out = 0).
3. Pay it out with RC6 to where it should stop, switch to the middle,
   measure the line, enter it and Set paid-out limit here. The run time
   between the two marks gives the line speed, used both ways.
4. Finish. A mission starting closes the calibration too.

The paid-out mark replaces `max_payout_m`; it and the wound-up mark bound
RC6 hand drive, Testing -> Mechanism and the mission's lower and stow, and
WinchDrop releases from no higher than the line less 0.5 m (the venue's 5.5 m
reach on a 6 m spool). A line shorter than 1.5 m is refused. Limits and the
line position are kept in `winch_limits.json` in the measured-state
directory; the position is saved at every stop, so a restart does not assume
the line is wound in. Before a calibration hand drive is unlimited, as
before. Without an encoder the estimate drifts with load and repeated jogs:
mark wound-up again whenever the hook is home. Uncalibrated, the L298N stows
at `payout_rate_mps`: the 0.45 m/s `stow_rate_mps` estimate stopped an
equal-speed motor with a third of the line out. Software-tested
(`sim/test_gcs_calibrations.py`); not yet performed on the aircraft.

### Sensors and mechanism

Scan frames run driver -> lidar -> body. The driver publishes `/scan_driver`.
`scan_mount` turns it by `driver_yaw_deg` into `/scan_raw`, the lidar's own
frame, with its marked 0 degrees at bearing 0, counter-clockwise. The mount
(`lidar_yaw_deg`, `mirrored`, or the saved calibration) then gives `/scan`
in the body frame. `sllidar_ros2` publishes bearing = pi - C1 angle, so its
C1 front arrives at 180 degrees. `lidar_model:=c1` sets `driver_yaw_deg` 180;
the LD06 uses 0. Mount yaw 0 means the C1's front faces the airframe nose.
Calibration and `scripts/check_sensors.py` measure in `/scan_raw`.

The GCS LiDAR calibration panel provides the full measured workflow, while
disarmed and stationary. GPS is unnecessary:

1. Measure the optical centre's X forward, Y left and Z up from the airframe
   base_link origin. Enter roll and pitch measured with a level. These cannot
   be inferred from an unknown room; level the scanner within 3 degrees.
2. Remove the calibration panel and capture the background after 2 seconds.
3. Put a matte panel at least 30 cm wide straight ahead, parallel to the nose
   from the optical centre. Enter the measured optical-centre-to-panel-face
   distance and capture after 2 seconds. Repeat farther ahead, at least 0.5 m
   beyond the first distance, then to port and starboard at +90/-90 degrees.
   Square each panel face to that direction and keep its centre in the laser plane.
4. Each capture requires 15 distinct fresh scans, at least five adjacent
   panel returns, stable edges, and at most 25 mm range variation. Background
   subtraction must identify exactly one panel. Spikes, clutter, stale or
   repeated timestamps and ambiguous targets are refused.
5. Review yaw, mirror direction and the two-distance range scale/bias fit.
   Independent port/starboard checks must remain within 2 degrees and 30 mm;
   implausible scale/bias corrections are refused. Apply only a passing result.
6. Reconnect the runtime to establish a new map after a mount change. Check
   forward/left/right bearings, measured wall distances and airframe shadows.

The saved record includes XYZ, roll/pitch/yaw, scan direction, range correction
and per-capture quality. `/scan` carries corrected bearings/ranges; measured
`base_link -> lidar_calibrated` TF carries translation and residual tilt,
so its rays match the complete physical mounting rotation. Avoidance's existing
capture-time transform path uses that measured frame. A running mapping session
holds if its mounting transform changes instead of mixing two geometries.
Legacy yaw-only files remain readable and are labelled position unmeasured.
Reported errors are repeatability/validation bounds, not a claim of exact
physical calibration. `scripts/check_sensors.py lidar` remains a quick two-target
bearing diagnostic. Saved mounting calibration takes precedence over launch
defaults. Use `scripts/check_sensors.py camera` to
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

**Manual flight mode** (30 Oct 2026). A connection profile's Mode is
"Mission (full stack)" or "Manual flight (servo, winch, camera feed and GCS
only)" (profile `mode` `mission` / `manual`, launch `manual:=true`). In manual
mode the transmitter flies and the Pi runs only MAVROS, `stream_rate_keeper`
(RC channels at 10 Hz), `rc_in_bridge`, `camera_ctrl` (channel 8 tilt, Camera
cal), `winch_ctrl` (RC6 hand drive, Winch cal), the aggregator (GCS telemetry
and commands) and the raw webcam feed (`usb_cam`, `camera_exposure`,
`web_video_server`; the GCS shows "Raw camera" only). No perception, lidar,
SLAM, avoidance, readiness, mission executive or execution service starts,
and the host refuses every task Start ("manual mode runs no missions or
tests"). The
router is a host service and serves Mission Planner in both modes. Switch by
selecting the profile in Connections, Disconnect (disarmed), Connect; the last
connected auto-connect profile is the one the Pi starts at boot. On the
aircraft profile `vehicle_manual` ("Drone manual (servo + winch)") is the
manual copy of `vehicle`. Checked on the aircraft: exactly those nodes,
output 5 holding the saved Camera cal points, the winch IDLE on RC6, Start
refused, and the raw feed at about 30 fps through the GCS video proxy once
the webcam was attached (receipt `.scratch/manual_mode_20261030/`; `sim/test_manual_mode.py`).

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

### World maker for hand-flown GCS testing

`tools/world_editor/serve.py` (port 8777, run in WSL; also the `world-maker`
entry in `.claude/launch.json`) places every arena component and takes the
arena dimensions as the GCS's own fields (`mission_bt.arena_dimensions`, same
labels, ranges and units). `world_spec.apply_dimensions` rebuilds the world
from them: lane length, width and walls; return-lane spacing and side; banner
size, lower edge and placement (rod-hung); QR sides; red-zone side; and
obstacle reach at 95% of wall height. Positions stay the operator's. A world
edited away from its dimensions is refused. Size limits are the GCS field
ranges (`world_spec.gcs_range`, e.g. corridor width 1-10 m); clearance checks
still apply, so a 1.8 m lane with half-width obstacles is refused (0.90 m gap).
Banners carry no wording and red zones built here none either (the white
border is the GCS red-zone border). Green, exit, orange and red come from the
editor's HEX fields and print in Gazebo. With an exit shade (field PDF) the
exit corridor's hung and laid boards print in it and there are no orange
boards; without one, orange marks the far opening of both corridors. With
GCS dimensions the banner border, the laid board's own height (Ground banner
height), the obstacle height and the QR white border follow the fields (QR
border 0: the code printed without its quiet zone). Markers are AprilTag
36h11 boards by default (`qr.kind`, `qr.ids`; the start marker carries the
target pad's ID), the border their white margin. A laid sheet over the
delivery zone is drawn on the zone's slab. **6 organiser points** turns the fence into six draggable points
P1-P6, listed with latitude/longitude once the simulator is connected. Saving writes the same values as
GCS preset `World NAME` to `~/.aerothon/dimension_presets.json`.
**Save & launch simulator** runs the laptop-simulation route for that world:
`launch_laptop_sim.sh` (Gazebo window, SITL, gateway on 8090) plus the real
web host serving the GCS on 8899. It also saves a selected, non-autoconnecting
`World maker simulation` profile in `~/.local/state/aerothon-world-sim`.
Nothing connects, arms or starts. In the GCS, Connect starts the production
runtime; the operator then loads and applies the preset and enters the banner
HEX codes and the geofence. The editor shows those values; geofence lines are
georeferenced on the FCU home, which is SITL's default site, not Gazebo's
world origin. Stop disconnects through the web host's disarm gate and refuses
while armed. The scripted graded run (`run_custom_world.sh`) remains separate.
The profile selects `sim_gazebo/config/world_sim_venue.yaml`: `venue.yaml`
plus two simulation-only values, the measured search braking
(`search_brake_mps2` 0.8) and a 1.0 m/s corridor cruise; a test keeps the
rest equal to the aircraft's file. Its camera delivers 960 x 540.

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
