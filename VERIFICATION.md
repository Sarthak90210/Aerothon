# VERIFICATION LOG

Append-only record of what has actually been proven, and how.

**Rules for this file**
1. One section per phase (see `PHASE_PLAN.md`), one entry per claim.
2. Every entry states: **Claim → Method → Raw output → Verdict**.
3. A verdict is `VERIFIED`, `PARTIAL`, `BLOCKED` or `FAILED`. Nothing else.
4. `VERIFIED` requires evidence a third party could re-run. "It looked right" is not a method.
5. Entries are never edited to look better. A `FAILED` entry stays; a later `VERIFIED` entry supersedes it and says so.

**Why this file exists.** `CURRENT_PROGRESS_HANDOFF.md` records a stack with 13 passing tests and a mission that timed out to success while sitting disarmed at a 54° tilt. Passing tests were not evidence because nothing tied a test to the behaviour it claimed to cover. Every entry here names the specific defect it closes.

---

## Phase 0 — Test harness and minimal fail-closed rails

**Date:** 2026-08-15
**Scope:** evidence tooling, launcher idempotency, geometry audit, and the four minimal fail-closed rails. Perception, avoidance and mission logic are explicitly *not* in scope — those are P1–P9.

---

### 0.1 — Test non-vacuity (meta-verification)

**Claim:** The Phase 0 tests fail when the defect they describe is reintroduced, so a pass is meaningful.

**Method:** Mutation testing. Each rail's implementation was reverted to its pre-Phase-0 behaviour in place, the corresponding test selection was run, and the source was restored from backup.

**Raw output:**

```text
###### MUTATION 1: remove the disarmed-setpoint gate (restore old behaviour)
FAILED sim/test_phase0_rails.py::TestSetpointGate::test_disarmed_setpoints_are_suppressed
FAILED sim/test_phase0_rails.py::TestSetpointGate::test_gate_closes_again_on_disarm_mid_flight
================== 2 failed, 2 passed, 18 deselected in 0.65s ==================

###### MUTATION 2: reset does not invalidate the tree (old memory-sequence bug)
FAILED sim/test_phase0_rails.py::TestTreeReset::test_restart_after_reset_is_deterministic
FAILED sim/test_phase0_rails.py::TestTreeReset::test_tree_advances_then_resets_to_waiting
================== 2 failed, 2 passed, 18 deselected in 0.65s ==================

###### MUTATION 3: guard ignores attitude (old guard)
FAILED sim/test_phase0_rails.py::TestAttitudeAbort::test_guard_trips_on_excessive_attitude
================== 1 failed, 4 passed, 17 deselected in 0.64s ==================

###### RESTORED — full suite
35 passed in 0.83s
```

**Verdict:** `VERIFIED`. Each mutation failed exactly the tests scoped to it and no others. This entry is a precondition for trusting 0.2–0.5 below.

---

### 0.2 — Rail: no setpoints to a disarmed aircraft

**Claim:** `Mav` never publishes to `/mavros/setpoint_position/local` while the FCU reports disarmed.

**Defect closed:** handoff §"Mission logic defects" — *"The mission may continue publishing setpoints while disarmed."*

**Method:** `sim/test_phase0_rails.py::TestSetpointGate`, 4 tests, against a **real** `rclpy` node and the **real** `Mav` object (not `MockMav`), with `pub_sp.publish` replaced by a recorder. Covers: disarmed suppression, armed pass-through, mid-flight disarm re-closing the gate, and no-setpoint-requested.

**Raw output:**

```text
TestSetpointGate::test_armed_setpoints_flow PASSED
TestSetpointGate::test_disarmed_setpoints_are_suppressed PASSED
TestSetpointGate::test_gate_closes_again_on_disarm_mid_flight PASSED
TestSetpointGate::test_no_setpoint_when_none_requested PASSED
```

**Verdict:** `VERIFIED` at unit level. Live-stack confirmation in 0.6.

---

### 0.3 — Rail: external intervention resets the mission

**Claim:** An external DISARM, or an uncommanded mode change into LAND/RTL, raises a mission-reset request; a landing we commanded ourselves does not.

**Defect closed:** handoff §"Current runtime state" — the tree reported `GOTO_CORRIDOR` while disarmed on the ground; and §"Mission logic defects" — *"External LAND/DISARM does not reset the behaviour tree."*

**Method:** `sim/test_phase0_rails.py::TestExternalIntervention`, 6 tests on the real `Mav`. Distinguishes our own commanded mode changes (5 s ownership window) from outside intervention, and asserts `consume_reset()` clears `mission_started`, `abort_requested` and the stale setpoint, and cannot fire twice.

**Raw output:**

```text
TestExternalIntervention::test_commanded_landing_disarm_is_not_an_intervention PASSED
TestExternalIntervention::test_consume_reset_clears_mission_state PASSED
TestExternalIntervention::test_external_disarm_requests_reset PASSED
TestExternalIntervention::test_external_mode_change_requests_reset PASSED
TestExternalIntervention::test_idle_aircraft_does_not_reset PASSED
TestExternalIntervention::test_our_own_rtl_is_not_an_intervention PASSED
TestExternalIntervention::test_new_start_clears_stale_expect_disarm PASSED
TestExternalIntervention::test_new_start_clears_stale_attitude_violations PASSED
```

**Verdict:** `VERIFIED` at unit level.

---

### 0.3b — Defect found in the Phase 0 work itself: stale state leaked across runs

**Claim:** State latched during one mission must not survive into the next.

**How it surfaced:** review of the Phase 0 code, not a test failure. The `Land` leaf sets `expect_disarm` so its own touchdown is not misread as an intervention — but nothing cleared it. After one completed mission the watchdog would have been **permanently deaf to external disarms** for every subsequent run: exactly the defect Phase 0 exists to close, reintroduced by its own fix. The same leak applied to `abort_reason` and the attitude violation counter.

**Fix:** `Mav._on_start()` now clears `_expect_disarm`, `abort_reason` and `_attitude_violations` alongside the already-cleared result latch.

**Method:** two new tests, mutation-checked by removing the clearing lines.

**Raw output (mutation — clearing lines removed):**

```text
FAILED sim/test_phase0_rails.py::TestExternalIntervention::test_new_start_clears_stale_attitude_violations
FAILED sim/test_phase0_rails.py::TestExternalIntervention::test_new_start_clears_stale_expect_disarm
2 failed, 22 deselected in 1.73s
```

**Raw output (restored):**

```text
37 passed in 2.71s
```

**Verdict:** `VERIFIED` fixed.

---

### 0.4 — Rail: the tree actually returns to WAITING (and restart is deterministic)

**Claim:** After an intervention the py_trees memory `Sequence` does not resume mid-mission; the next tick is at `WaitForMissionStart`, and a fresh START begins at `SetModeArm`.

**Defect closed:** handoff §"Mission logic defects" — *"Abort/start restart semantics are incomplete because the memory sequence can retain progress."*

**Method:** `sim/test_phase0_rails.py::TestTreeReset`, 4 tests. Builds the **real** root via `build_root()`, ticks it into `Takeoff`, injects an external disarm through `Mav._on_state`, applies `apply_pending_reset()`, and asserts the tip. Also asserts the latched `INTERRUPTED` result and that a no-reset tick does not disturb a healthy mission.

**Raw output:**

```text
TestTreeReset::test_no_reset_means_no_interference PASSED
TestTreeReset::test_reset_latches_interrupted_result PASSED
TestTreeReset::test_restart_after_reset_is_deterministic PASSED
TestTreeReset::test_tree_advances_then_resets_to_waiting PASSED
```

**Verdict:** `VERIFIED` at unit level.

---

### 0.5 — Rail: excessive-attitude abort, and latched mission outcome

**Claim (a):** A sustained roll/pitch beyond the limit trips the abort guard with a stated reason; a single noisy sample does not.
**Claim (b):** `/mission/result` latches exactly one terminal outcome per run as JSON with an explicit reason.

**Defect closed:** handoff §"Live evidence of current failures" — the aircraft sat at RPY `[-53.786, 5.925, -177.882]` against a corridor wall and no part of the stack objected; and §"Mission logic defects" — *"Completion and failure states are not robustly latched/reported."*

**Method:** `sim/test_phase0_rails.py::TestAttitudeAbort` (5 tests) and `::TestMissionResult` (3 tests). The attitude tests replay the **actual recorded failure attitude** (−53.8° roll, 5.9° pitch) through the real quaternion→RPY path and assert both the recovered angles and that `CheckAbortTriggered` trips.

**Raw output:**

```text
TestAttitudeAbort::test_guard_trips_on_excessive_attitude PASSED
TestAttitudeAbort::test_level_flight_is_not_excessive PASSED
TestAttitudeAbort::test_roll_pitch_recovered_from_quaternion PASSED
TestAttitudeAbort::test_single_noisy_sample_does_not_trip PASSED
TestAttitudeAbort::test_sustained_tilt_trips_after_n_samples PASSED
TestMissionResult::test_new_start_clears_previous_result PASSED
TestMissionResult::test_result_is_latched_first_writer_wins PASSED
TestMissionResult::test_result_payload_is_json_with_reason PASSED
```

**Verdict:** `VERIFIED` at unit level.

---

### 0.6 — LIVE stack run: all four rails against real SITL

**Claim:** Every Phase 0 rail holds against the real stack — real Gazebo Harmonic, real ArduPilot SITL, real MAVROS, real behaviour tree — not just against unit-test doubles.

**Method:** `sim/verify_phase0_live.py`. Scripted reproduction of the exact scenario from `CURRENT_PROGRESS_HANDOFF.md`: start the mission from the GCS topic, let it arm and climb, then **force-disarm from outside the behaviour tree** the way Mission Planner or the safety pilot would, and assert the tree fails closed.

Force-disarm uses `MAV_CMD_COMPONENT_ARM_DISARM` with `param2 = 21196`. An ordinary `CommandBool(false)` is **rejected by ArduPilot while airborne** — the first attempt at this test reported `armed=True` for exactly that reason.

**Raw output:**

```text
======================================================================
 PHASE 0 LIVE RAIL VERIFICATION
======================================================================

[0] Stack connectivity
  [PASS] MAVROS reports FCU connected  (mode=STABILIZE)
  [PASS] mission_bt is publishing /mission/state  (state=WAITING)

[1] Pre-start state
  [PASS] tree is parked at WAITING before START  (state=WAITING)

[2] Setpoint gate while disarmed and idle (6s)
  [PASS] no setpoints published while disarmed (idle)  (0 setpoints observed)

[3] Mission start
  [PASS] tree leaves WAITING on START  (state=ARMING)
  [PASS] aircraft armed  (armed=True mode=GUIDED)
  [PASS] aircraft climbing under mission control  (alt=1.56 m state=TAKEOFF)
      stage before intervention: TAKEOFF

[4] External DISARM (simulating Mission Planner / safety pilot)
  [PASS] aircraft disarmed from outside the tree  (armed=False)

[5] Fail-closed reset
  [PASS] tree returned to WAITING after intervention  (state=WAITING (was TAKEOFF))
  [PASS] tree is NOT stuck at a stale stage  (state=WAITING)
  [PASS] /mission/result latched an outcome
         ({"state": "INTERRUPTED", "reason": "external disarm", "t": 60.8})
  [PASS] result carries an explicit reason  (state=INTERRUPTED reason=external disarm)

[6] Setpoint gate after intervention (6s)
  [PASS] no setpoints published to the disarmed aircraft  (0 setpoints observed)

======================================================================
 PHASE 0 LIVE: 13/13 checks passed
======================================================================
```

**Direct comparison with the handoff's recorded failure:**

| Handoff (before) | This run (after) |
|---|---|
| `Armed: false`, `Mission state: GOTO_CORRIDOR` | `armed=False`, `state=WAITING` |
| no failure reason anywhere | `INTERRUPTED — external disarm` |
| mission kept publishing setpoints while disarmed | 0 setpoints observed while disarmed |

**Verdict:** `VERIFIED`.

---

### 0.6b — Rail: abort latches (defect found by the live run)

**Claim:** Once an abort fires, the mission must not resume.

**How it surfaced:** the **first** live run, not a unit test. `/mission/result` latched:

```text
{"state": "ABORTED_RTL", "reason": "Excessive attitude (roll=-17.8 pitch=46.3)", "t": 80.2}
```

The attitude rail correctly fired during takeoff and commanded RTL. But the tree then reported `TAKEOFF` again. Every guard condition is **level-triggered** — attitude recovers once RTL levels the aircraft, battery voltage recovers under reduced load, the FCU reconnects — so the guard released and the memory `Sequence` resumed its previous leg **while the aircraft was already flying itself home**.

**Fix:** `Mav.abort_latched`. `CheckAbortTriggered` returns SUCCESS unconditionally once latched, and the latch clears only on an explicit new START or a mission reset. The first reason wins, so the latched cause is never overwritten by a later symptom.

**Method:** two new unit tests plus mutation check.

**Raw output (mutation — latch check removed):**

```text
FAILED sim/test_phase0_rails.py::TestAttitudeAbort::test_abort_latch_clears_only_on_new_start
FAILED sim/test_phase0_rails.py::TestAttitudeAbort::test_abort_latches_and_does_not_resume
2 failed, 2 passed, 22 deselected in 1.98s
```

**Verdict:** `VERIFIED` fixed. This defect was invisible to unit testing and only appeared under real flight dynamics — it is the strongest argument for the live-evidence half of the per-phase evidence pack.

---

### 0.7 — Regression: pre-existing suite still passes

**Claim:** Phase 0 changes do not break the existing behaviour-tree and aggregator tests.

**Method:** Full offline suite via the new `scripts/run_tests.sh`. `MockMav` was extended with the new commander API (`attitude_excessive`, `expect_disarm`, `publish_result`, `consume_reset`) — the three initial failures were the mock lagging the interface, not a behaviour regression.

**Raw output:**

```text
=== Python unit tests ===
...................................                                      [100%]
35 passed in 0.93s
  -> ok
=== Python syntax (all mission/perception/GCS/sim sources) ===   -> ok
=== Shell syntax ===                                             -> ok
=== XML / YAML well-formedness ===                               -> ok
====================== ALL OFFLINE CHECKS PASSED =====================
```

**Verdict:** `VERIFIED`.

---

### 0.9 — Defect found and fixed: the test suite was poisoning its own imports

**Claim:** Test results were order-dependent. Both pre-existing test files installed a `MagicMock` in place of `mavros_msgs` for the entire pytest session, so any test file collected after them silently received mocks instead of real ROS messages.

**How it surfaced:** `sim/test_phase0_rails.py` passed when invoked directly but **22 of its 35 tests failed** under `pytest sim/`. pytest collects alphabetically, so `test_behavior_tree.py` imported first and poisoned `sys.modules`.

**Root cause:** the guard was

```python
if 'mavros_msgs' not in sys.modules:   # WRONG
```

On a machine that *has* `mavros_msgs`, the module is simply not imported *yet* — so this condition is true and the mock gets installed regardless. The intent was "mock only if unavailable"; the test performed was "mock unless already imported".

**Fix:** replaced with a real availability check in both files:

```python
try:
    import mavros_msgs.msg
    import mavros_msgs.srv
except ImportError:
    ...install mocks...
```

**Method of verification:** ran the suite in three collection orders.

**Raw output:**

```text
-- directory collection --      35 passed in 0.85s
-- reversed order --            35 passed in 0.85s
-- behaviour tree first --      29 passed in 0.84s   (subset: 2 files only)
```

**Verdict:** `VERIFIED` fixed. **Significance:** this is the same class of defect as the handoff's central complaint — a green suite that was not testing what it appeared to test. Any earlier claim resting on `pytest sim/` output predating this fix should be treated as unproven.

---

### 0.8 — Environment: the simulation overlay was missing

**Claim:** The ArduPilot/Gazebo overlay this project depends on had been destroyed, and the launcher's dependency check correctly refused to run without it.

**Method:** `scripts/preflight_stack.sh` after the previous session's stack died.

**Raw output:**

```text
PASS  ROS 2 Jazzy command
PASS  Gazebo Harmonic command
FAIL  MAVROS package
FAIL  ros_gz bridge package
FAIL  slam_toolbox package
FAIL  web_video_server package
FAIL  ArduPilot SITL launcher (sim_vehicle.py)
FAIL  ArduPilot ROS/Gazebo bringup package
FAIL  ArduPilot Gazebo model/plugin package
```

**Root cause:** the overlay had been built into `/tmp/ardupilot_stack2`. `/tmp` was cleared, taking `sim_vehicle.py`, `ardupilot_gazebo` and `ardupilot_sitl` with it. The same event killed the process group (`176131`) that `CURRENT_PROGRESS_HANDOFF.md` reported as still running.

**Note on this output:** the four MAVROS/ros_gz/slam_toolbox/web_video_server rows are a **false alarm in the check script itself** — those packages are present in `/opt/ros/jazzy`, but `preflight_stack.sh` never sources `/opt/ros/jazzy/setup.bash`, only the overlay. Confirmed present:

```text
mavros                   /opt/ros/jazzy
ros_gz_bridge            /opt/ros/jazzy
slam_toolbox             /opt/ros/jazzy
web_video_server         /opt/ros/jazzy
```

Only the three ArduPilot rows were real failures.

**Verdict:** `VERIFIED` as a diagnosis. Two follow-ups, both done: (a) the overlay is rebuilt persistently via the new `scripts/install_ardupilot_overlay.sh` into `~/aerothon_stack`; (b) `preflight_stack.sh` now sources the ROS distro before checking distro packages, removing the four false failures.

---

### 0.10 — Overlay rebuild: three upstream build blockers and how each was resolved

**Claim:** The ArduPilot/Gazebo overlay can be rebuilt from scratch on this machine **without root**, reproducibly.

**Method:** iterative `scripts/install_ardupilot_overlay.sh` runs, each failure diagnosed and encoded back into the script so the next machine does not hit it.

| # | Blocker | Diagnosis | Resolution |
|---|---|---|---|
| 1 | `Could not checkout ref 'Copter-4.6'` | There is no `Copter-4.6` branch upstream; newest stable is `Copter-4.5`. `goal.md` says "4.5/4.6". | Pinned `Copter-4.5`. |
| 2 | `ardupilot_gazebo`: `gstreamer-1.0`, `gstreamer-app-1.0` not found | Only the GStreamer *runtime* libs are installed; `-dev` needs root. Used by exactly one target, `GstCameraPlugin` (RTP video streaming), which this project does not use — camera frames reach ROS via the gz camera sensor + `ros_gz` bridge. | `scripts/patch_ardupilot_gazebo_gst.py` makes GStreamer optional and guards that one target. Applied only when GStreamer is absent. |
| 3 | `ardupilot_sitl`: `microxrceddsgen` not found | `Tools/ros2/ardupilot_sitl/CMakeLists.txt` hardcodes `--enable-dds`. The generator's bundled Gradle 7.6 rejects JDK 21 ("class file major version 65"); bumping to Gradle 8.5 then fails in the vendored `IDL-Parser` submodule (`classifier` property removed in Gradle 8). Installing JDK 17 needs root. | `scripts/patch_ardupilot_sitl_dds.py` removes `--enable-dds`. AP_DDS is unused: the locked architecture reaches the FCU over MAVLink/MAVROS. Applied only when `microxrceddsgen` is absent. |

**Also fixed in the installer along the way:** `vcs import` runs three times with backoff (a parallel clone was refused by GitHub once), and its success is no longer trusted on exit code alone — the script now verifies `sim_vehicle.py`, `ardupilot_gazebo/CMakeLists.txt` and `modules/mavlink` actually exist, because `vcs` reports success even when an individual repo failed to check out its ref.

**Both patches are:** idempotent, backed up to `*.aerothon-orig`, applied **only** when the proper dependency is missing, and documented in-file with the exact `sudo apt` command to get the unpatched build instead.

**Standing caveat:** two upstream source files in `~/aerothon_stack` are locally modified. They are outside this repository, and re-running `vcs import` may revert them — the installer re-applies both on every run, so re-running it is the correct recovery.

**Raw output (final run):**

```text
Summary: 7 packages finished [2min 32s]
PASS  sim_vehicle.py on PATH
PASS  arducopter SITL binary built
PASS  ardupilot_gazebo package
PASS  ardupilot_gz_bringup package
PASS  ardupilot_sitl package
 Overlay installed at: /home/sarthak/aerothon_stack
```

**Verdict:** `VERIFIED`. `scripts/preflight_stack.sh` subsequently reports 9/9 PASS.

---

### 0.11 — Live stack brought up: three launch defects fixed

**Claim:** `scripts/launch_level6_sim.sh` brings up a stack in which MAVROS actually reaches the flight controller.

Three defects blocked this; none were in the handoff.

**(a) The reaper killed its own launch.** The straggler pattern included `launch_level6_sim`, which matches this script, any shell wrapping it, and any process whose command line merely mentions it. The first run killed its own parent. Fixed twice over: stragglers are now matched by `ps` **excluding our own process group**, and the pattern no longer contains `launch_level6_sim` at all (previous launcher instances are handled by the recorded PGID).

**(b) ArduCopter was crash-looping on DDS parameters.**

```text
PANIC: Failed to load defaults from .../copter.parm,.../gazebo-iris-gimbal.parm,
       .../dds_udp.parm,.../dds_use_ns.parm
Running: sh dumpstack.sh 29609 ... Failed
```

Upstream `iris.launch.py` defaults the `defaults` argument to a list including `dds_udp.parm` and `dds_use_ns.parm`. Those name AP_DDS parameters, and since 0.10(3) built the firmware without AP_DDS, ArduPilot panicked on unknown parameters. Symptom at the top of the stack was simply `connected: false` with no error. Fixed **without patching upstream** — `sim_full.launch.py` now passes an explicit `defaults` omitting the DDS files, which is correct whether or not DDS is compiled in.

**(c) Nothing was feeding the MAVLink router.**

```text
Router status: 53 pkts routed | 0 FCU, 1 MAVROS, 0 GCS endpoints active.
```

The launcher started `mav_router.py --fcu-in 14560`, but `ardupilot_gz`'s `robot.launch.py` computes `mavlink_out = 14550 + port_offset` and hands it to MAVProxy, so with instance 0 the stream lands on `127.0.0.1:14550`. The router's *GCS* port was also 14550, so MAVProxy's stream arrived on the wrong side of the router. Fixed: router FCU input is now 14550, its GCS listen moved to 14552, and its fan-out to 14553. MAVProxy's hardcoded second `--out 127.0.0.1:14551` remains the Mission Planner endpoint for SITL, and the launcher now prints that correctly.

**Raw output after all three fixes:**

```text
connected: true armed: false mode: STABILIZE
```

**Verdict:** `VERIFIED`.

---

### 0.12 — Evidence pack captured

**Claim:** `scripts/capture_evidence.sh` produces a reviewable pack from the live stack.

**Raw output:**

```text
[1/6] Graph inventory captured.
[2/6] Topic census captured (24 topics).
[3/6] Recording 25 topics for 20s...
[3/6] rosbag written.
subscribing to: ['/camera/image', '/percep/qr/annotated']
/camera/image: saved camera_image.jpg (480, 640, 3)
/percep/qr/annotated: saved percep_qr_annotated.jpg (480, 640, 3)
[4/6] Camera frames saved: 2.
[5/6] TF tree unavailable (tf2_tools missing or no transforms).
[6/6] Screenshot failed.
```

```text
Bag size:   273.5 MiB      Messages: 2663      Duration: 18.6s
Storage:    mcap           Distro:   jazzy
```

Pack: `evidence/P0/20260815-202023-rails-live/`

**Defect found and fixed in the tool itself:** the first capture reported "no image topics present" while `/camera/image` was publishing at 5 Hz. ROS 2 discovery is asynchronous, and the script called `get_topic_names_and_types()` immediately after node construction. It now spins until discovery completes.

**Second defect in the tool, found while auditing the pack:** the script reported `[5/6] TF tree unavailable` — but the pack in fact contains `frames_2026-08-15_20.22.20.pdf` and its `.gv` source. `tf2_tools view_frames` writes a **timestamped** filename; the script checked for a literal `frames.pdf`. The TF tree was captured correctly all along and the tool was lying about its own output. Now globbed with `find -name 'frames*.pdf'`.

**Pack contents (verified on disk, 274 MB):**

```text
camera_image.jpg              percep_qr_annotated.jpg
frames_2026-08-15_20.22.20.pdf / .gv     graph_inventory.txt
manifest.txt                  topic_census.txt      topic_list.txt
rosbag/ (mcap, 2663 msgs)     rosbag_record.log     frame_capture.log
```

**Known degraded, not fixed:** desktop screenshots fail in a non-graphical shell. Reported honestly rather than silently skipped; they work when run from a desktop session.

**Verdict:** `VERIFIED` for rosbag, census, inventory, camera frames, TF tree and manifest. Screenshot capture remains environment-dependent.

---

### 0.13 — Defects found live that Phase 0 does NOT fix

These were discovered while proving the rails. They are recorded here so they are not rediscovered later as surprises, and are **out of Phase 0 scope** by design.

**(a) The aircraft cannot hold a stable climb.** The attitude rail aborted a takeoff at `roll=-17.8 pitch=46.3` at 1.5 m altitude. Pose is published at only ~1.5–2.8 Hz (see (c)), so the 5-sample debounce corresponds to roughly **1.8 seconds sustained** beyond 45° — this is a real sustained tilt, not a sensor spike or a twitchy threshold. It is the same signature as the handoff's recorded `RPY [-53.786, 5.925, -177.882]`. Suspected cause: `scripts/materialize_vehicle_model.py` adds lidar and camera links to the Iris, changing mass and inertia. **Owner: Phase 2** (before any camera-pointing work, per the plan's "stabilize frames and basic flight before autonomy").

**(b) The mission runs while the aircraft is on the ground.** A later run reached `CORRIDOR_NAV` with the aircraft at `x=9.28, y=1.47, z=0.117` — 11 cm altitude, armed, in GUIDED, crawling along the ground while the tree reported corridor navigation. Altitude is never a success condition for any stage. **Owner: Phase 5** (corridor traversal), with the general fix in Phase 10 (every transition needs a sensor/flight success condition).

**(c) Telemetry stream rates are far too low.** Measured live:

```text
/mavros/local_position/pose      average rate: 1.504 – 2.776
/scan                            average rate: 6.773
/camera/image                    average rate: 4.910
```

`goal.md` Q14 specifies 10 FPS for QR and Q27 requires LiDAR ≥ 8 Hz. Position at ~2 Hz is not adequate for closed-loop guidance, and `/scan` at 6.8 Hz already fails the stated interlock. Stream rates must be requested explicitly from ArduPilot (`SR*` parameters / `MAV_CMD_SET_MESSAGE_INTERVAL`). **Owner: Phase 2**, since every later perception loop's timing budget depends on it.

**(d) Pose topic takes 30–60 s to appear** after MAVROS connects, with no indication anywhere. Belongs in the Phase 10 readiness interlock as an explicit "waiting for EKF origin" state rather than an unexplained silence.

**Verdict:** `FAILED` as flight behaviour — recorded, assigned, and deliberately not patched in Phase 0.

---
