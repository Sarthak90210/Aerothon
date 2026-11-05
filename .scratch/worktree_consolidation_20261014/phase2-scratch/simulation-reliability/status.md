# 2026-10-13 afternoon: Phase 2 FINAL -- every combination on the final code

Branch `phase2-arena` at 1447666; main tree byte-identical for every changed
file. Frozen as V44: `logs/reliability_reduced_scope_v44_source_20261013/
provenance.json` (987 files, 7 changed since V43, archive 2194fb57...;
accepted_source false). Every flight entered the dimensions at the GCS.

## Rendered (Gazebo + ArduPilot SITL), banners 1.15 m, seed 20261003 -- p2r11

| World | Result | Flight | Drop err | Landed | Closest obstacle |
|---|---|---|---|---|---|
| laid only | PASS 22/22 | 874.0 s | 0.15 m | 0.12 m | 0.72 m |
| hung only | PASS 22/22 | 832.0 s | 0.15 m | 0.08 m | 0.71 m |
| hung + laid | PASS 22/22 | 819.1 s | 0.14 m | 0.14 m | 0.77 m |

## Headless (navigation grade), final code -- 16/16 PASS
4 worlds (both, hung, laid, both with 5 m corridors) x banner 1.15 m and
0.30 m x calm (s1) and field (s2): `../AEROTHON_phase2/logs/p2v44_*_20261013`.

## Offline -- final code
`run_tests.sh --reduced-scope`: 1920 passed, 8 skipped; syntax, XML/YAML and
GCS frontend build ok (`logs/offline_v44_final_20261013.log`).

## Fixes since the morning entry (each from a rendered failure, each with a test)
- da3d2cd: release probes lift the empty claw 0.6 m before waiting (p2r6: claw
  dragged 2 m off the pad during a 13 s wait).
- 0f604d1: the return search hands its ground-ranged laid sheet to the
  square-up; a clipped sighting is noted when nothing better is known (p2r9
  laid-only: 49/82 at gate height, four sweeps, 1078 s).
- 1447666: the corridor controller skips a stub first waypoint (< 0.3 m) when
  the leg to the next is clear (p2r9 hung-only, p2r10 laid-only: crept at
  0.05 m/s straight at the first half-width obstacle until STUCK).
  The four user-deferred strong-gust stress tests fail with and without it.

## Open
- Merge `phase2-arena` into main and push: waiting for the user's go-ahead.
- Time margin: laid-only 874 s of 900 s; QR search is ~435 s of every flight.
- One rendered run per world on the final code (seed 20261003); earlier runs
  of the same worlds showed intermittent failures, each fixed above.

# 2026-10-13 early: Phase 2 (the clarified arena) -- final results

Branch `phase2-arena` (worktree `../AEROTHON_phase2`) at 7e04bb2; the main
tree carries the same 43 changed files (byte-identical, checked). Frozen as
V43: `logs/reliability_reduced_scope_v43_source_20261012/provenance.json`
(987 files, 50 changed since V42, archive f124fe00...; accepted_source false).

Every flight entered the arena dimensions at the GCS from a saved preset and
was held until the aircraft confirmed them (operator's path).

## Rendered (Gazebo + ArduPilot SITL), banners 1.15 m, seed 20261003, calm

| World | Run | Source | Result | Flight | Drop err | Landed |
|---|---|---|---|---|---|---|
| hung + laid ("both") | p2r2 | 85b792f | PASS 22/22 | 835 s | 0.14 m | 0.16 m |
| hung only | p2r2 | 85b792f | PASS 22/22 | 834 s | 0.13 m | 0.42 m |
| laid only | p2r5 | c8c3f4c | PASS 22/22 | 883 s | 0.14 m | 0.16 m |
| hung + laid ("both") | p2r6 | 7e04bb2 | FAIL 21/22 (claw drag) | 883 s | 0.21 m | -- |
| hung + laid ("both") | p2r7 | 7e04bb2 | PASS 22/22 | 859 s | 0.15 m | 0.03 m |

Laid-only failed twice before passing:
- p2r3 (85b792f): at gate height the laid sheet could not be re-identified
  (overflowing on the axis, foreshortened backed off) -> out of vantage points.
  Fix 36a6b4e: the sheet, once identified from above, is carried by where it
  lies; green at that spot at gate height is the sheet.
- p2r4 (36a6b4e): outbound passed; the return search looked level / -20 deg and
  ranged by area, never read the laid return sheet, passed 900 s (stopped).
  Fix c8c3f4c: on a gate learnt ground-only, the return search looks in GROUND
  from look height and ranges a sighting where it meets the ground.
The hung-only world is unaffected by both fixes (no laid sheet is ever
identified there, and placement is never learnt as ground).

p2r6 completed the mission (both gates square, delivery 0.15 m, precise
landing) but failed "no obstacle contact": after release the empty claw lay
on the field during a 16 s winch pause, the aircraft drifted, and the claw
dragged ~2 m off the pad (allowed only within 1 m), yanking the aircraft to
4.16 m. Winch drop code is unchanged in Phase 2; the 5.5 cm-tall payload
leaves the claw nearer the ground. p2r7, same code and seed, passed with the
claw touching only at the pad. Intermittent: see DIAGNOSIS.md in the p2r6 run.

Watch: laid-only took 883 s of the 900 s budget.

## Headless (navigation-only grade), calm
- Final campaign before these fixes: 16/16 (both heights, 4 worlds, calm+field).
- After 36a6b4e and after c8c3f4c: laid-only and both, navigation PASS each time.

## Offline
`bash scripts/run_tests.sh --reduced-scope`: 1915 passed, 8 skipped; syntax,
XML/YAML and GCS frontend build ok (`logs/offline_v43_final2_20261013.log`).
The first final run had 3 errors from a test leaking an rclpy context into the
next file; fixed in 7e04bb2.

## Not done / open
- 0.30 m banners: dropped from rendered qualification (user: the real banner
  is not that thin).
- Merge `phase2-arena` into main: waiting for the user's go-ahead.
- Field items in docs/FIELD_READINESS.md (lidar calibration now has a GCS mode).

# 2026-10-12 afternoon: Phase 2 (the clarified arena) in progress

Work is on branch `phase2-arena`, in the worktree `../AEROTHON_phase2`.
Its base commit d680ead snapshots the Phase 1 working tree. The main tree
is untouched while rendered r10 flies, because mission_bt is installed in
develop mode and edits there would leak into the running flights.

- Dimensions reach the aircraft only through the GCS, as at the competition
  (user instruction):
  - `scripts/gcs_operator.py` saves a preset over the aggregator's
    WebSocket the first time, applies it before START, and requires the
    aircraft's "applied" confirmation;
  - headless (`fly_headless.py --gcs-preset`) runs the aggregator and holds
    START until the dimensions are applied;
  - rendered (`AEROTHON_GCS_PRESET`) gives the mission no QR size at launch.
- Worlds are built from the same dimensions (`scripts/world_from_dimensions.py`):
  - side-by-side corridors;
  - a banner as wide as the corridor, hung from a rod at the 10 ft wall top,
    laid in front of the mouth, or both;
  - ORANGE banners at every opening the aircraft must not use;
  - exit-corridor obstacles reaching half the width;
  - one 5 ft red zone; 1 m QRs.

  Banner height is unknown (user: test several), so there are worlds at
  0.30 m and 1.15 m, and 5 m corridor variants. Presets are in
  `sim/arena_presets/`.
- Algorithm changes:
  - The banner search looks for green only once colours are supplied, so the
    adjacent orange banner is never a candidate.
  - The aspect limits stretch with the banner's own size from the GCS
    (`perception_banner/banner_shape.py`); a 3.5 x 0.3 m banner is 11.7:1.
  - The square-up descent never steps more than 0.8 x the banner height, and
    with the GCS's lower edge it aims the scan plane at the banner directly.
    The smoke run's 1 m steps went straight over a 0.3 m banner.
  - The precision landing uses the start QR's size from the GCS (it used the
    target pad's) and a commit height at which the marker fits at any
    rotation. The smoke run lost a 1 m QR turned 25 deg at 2.53 m and
    hovered there for 600 ticks.
- Passing under hung banners: after ducking under the green gate's banner
  the corridor is flown at that height, which clears a same-height orange
  banner at the far opening.
- Headless smoke run (0.30 m banner, suspended, calm) through the GCS path:
  completed in 813 s, ducked under both gates at 2.1 m; the landing was
  degraded (fixed above).
- Rendered Phase 1 results:
  - suspended r9 and both r9 completed with 21/22 checks, over time only
    (926 s, 918 s);
  - r10 (ground, both) is flying on the code with `_laid_face`.

# 2026-10-12 midday: laid sheet in front of the mouth; return-gate loop fixed

- The laid sheet now sits in front of the mouth (materialize_world
  laid_banner_x0), not half under the lane floor. Headless field s2 with
  it: ground-only 829 s and both 763 s, every navigation check passing;
  in `both` the two banners were aligned in turn.
- Headless calm ground-only failed twice at the return gate:
  1. ABORTED_RTL at 1090 s: the square-up measured the lidar from the 5 m
     search height, above the corridor walls. Fix: a GROUND pass descends
     to gate height before measuring (`_begin_square`).
  2. FAILED at 963 s (logs/laid_front2_ground_calm1_20261012, DIAGNOSIS.md):
     the lidar's face was the first slalom obstacle about 1 m inside the
     mouth, square to the lane, and the laid-face check refused anything
     farther than the sheet. Fix: `AlignToBanner._laid_face`. A farther
     face is used (the walls when visible, otherwise that face, with the
     sheet's ground range as the standoff). Only a nearer face (a side
     wall) still triggers the mouth move. Tests in
     sim/test_banner_placement_alignment.py (33 pass).
- Re-flying headless calm ground s1, calm both s1 and field ground s2 into
  logs/laid_front3_*_20261012. Rendered r10 (ground, both) picks up the fix
  (mission_bt is installed in develop mode).

# 2026-10-12 early hours: issue 43 fixed, rendered placements in progress

- Issue 43 (ground-only gate, side-wall square-up) is fixed in AlignToBanner's
  GROUND passes: an axis move, an edge-on-wall square-up and a far-face
  guard. Headless banner_ground passes all navigation checks at calm s1
  (822 s; it failed before) and field s2 (868 s). See issue 43.
- Full reduced offline suite on that source: 1842 passed, 8 skipped, all
  in-scope pass (logs/offline_v43_full_20261012.log).
- Rendered suspended r4 FAILED at the return gate. The banner detector
  identified the outbound corridor's green floor, seen into a frame corner
  between two white walls, as a bordered banner ~19 m off; the lidar never
  found a face. Fix: min_border_sides 2 -> 3, with a regression test in
  sim/test_banner_identity.py. The rendered r4 red-zone count (140 cells)
  matches earlier versions (136-138), so it is not a regression.
- After the detector change, re-flown: rendered ground (r5), then suspended
  and both (r6), all with AEROTHON_SITL_PORT_SHIFT=100. WSL came back from
  sleep unable to set up mirrored networking and runs loopback-only; the
  simulator is unaffected.
- Rendered banner_both r6 (logs/banner_rendered_banner_both_s20261003_20261011_r6):
  COMPLETED with every acceptance check passing except "flight within
  900 s" (1006 s). Both gates squared up, delivery 0.18 m, precise landing
  0.19 m. The GROUND glance missed the laid sheet: the gate posts were
  painted green and merged with it in the colour mask. Posts are now grey
  (mission2.sdf), with a test.
- Rendered runs between r4 and r6 were contaminated. An old
  velocity_controller from the stopped r4 run kept publishing stale-clock
  setpoints on ROS domain 30: suspended r6 stalled in the corridor (see
  its DIAGNOSIS.md), and ground r5 is suspect. The stop procedure now kills
  by ROS_DOMAIN_ID.
- Corridor floors are neutral grey (materialize_world NEUTRAL_FLOOR). A
  green floor between white walls looked like a framed banner.
- Measured rendered HSV: the laid sheet is H76/S199/V196 lit and V105 in
  shadow; the delivery-zone grass is H47/S73. The grass is below the S floor
  of 90, so the green band is unchanged.
- All three placements re-flown on the clean world into *_r8.
- **Rendered banner_both r8: GRADE_PASS**, all acceptance checks. Flight
  878 s, delivery 0.16 m, landing 0.14 m, minimum corridor clearance
  0.743 m (logs/banner_rendered_banner_both_s20261003_20261011_r8). It
  aligned on the hung board only: the GROUND glance refused the laid sheet
  at aspect 11.9 (949 x 80 px from 4.9 m out, 3.1 m up) against the board
  limit of 8. The GROUND pose now allows up to 16, mirrored in headless.
- Rendered banner_ground r8 aborted (DIAGNOSIS.md). In the GROUND pose the
  area floor refused the sheet at 12.4-13k px against 13,816; the floor now
  scales by sin(35 deg). Ground and both are re-flown as *_r9 on both fixes.
- Rendered suspended r8 was stopped at ~1000 s at the return gate.
  FindReturnBanner stood 3 m off the return board, which then overflows both
  sides of the frame, and min_border_sides=3 refused it. Border rule now:
  two sides are enough if OPPOSITE (a board wider than the frame), refused
  if ADJACENT (a patch in a frame corner, e.g. the old green floor). Tests
  cover both cases. All three placements are queued as *_r9 on the final
  detector.
- Still to do after the rendered runs: rerun the full offline suite, since
  the detector changed after the 1842-pass run, and freeze V43.

# Organiser clarifications implemented; banner placements flown headless 2026-10-11

Work on the user's instruction: adapt the algorithms to the SAE Aerothon 2026
clarifications, add the GCS fields, and fly every banner placement. This is
NOT an accepted source; rendered acceptance and the reduced campaign are not
yet rerun on it.

What changed (flown modules -- every earlier flight result is superseded):

- Banners carry no text. Identity is the 3-inch white border around a field
  of the operator-supplied colour (perception_banner/colours.py, HEX -> HSV
  band). The GCS has a colour field per banner; readiness requires them.
- Banners may be suspended, laid on the ground, or both. Each gate is one
  selector (mission_tree.align_to_every_banner): the hung view under a 60 s
  nothing-identified budget, flying back over the top before handing over; a
  3 s GROUND-pose glance gates a second, laid-sheet alignment; a ground-only
  pass; the unbudgeted hung pass last. A gate aligned only on the ground pass
  makes the next gate try the ground view first.
- New camera pose GROUND (-35 deg). The banner detector runs in FORWARD,
  BANNER and GROUND only, and in GROUND refuses a box narrower than 1.5:1 (a
  sheet seen end-on from beside the corridor).
- AlignToBanner ranges a laid sheet on the ground plane and refuses a lidar
  face that is not at the sheet's range.
- QR: appearance match against the start marker first, decoded message
  second; the evidence used is published as match_basis.
- GCS: flight starts (arm, takeoff, mission, test part) only in GUIDED;
  recovery commands work in any mode; a test-part selector.
- Worlds: fake green banners removed from flown worlds (banner_decoys.json
  keeps them as the negative control); corridors side by side.
- Headless fixture: models laid banners, applies the detector's pose gate and
  aspect limits, and never delivers a detection in its capture step. At zero
  camera latency (calm) every banner capture used to reach mission_bt before
  its /clock and was refused as from the future -- the cause of the V41
  my_world calm seed 1 failure ("best 0/0" at 13 vantage points).

Headless navigation matrix, final logic (navigation-only; the two payload
checks are not flown in that mode and fail by construction):

| world | field s2 | calm s1 |
|---|---|---|
| banner_suspended | all nav checks pass, 660 s | pass, 671 s |
| banner_both (both banners aligned in turn) | pass, 663 s | pass, 670 s |
| banner_ground | pass, 871 s (logs/banner_ground_aspect15_field2_20261011) | FAIL at outbound square-up, issue 43 |
| my_world | pass, 704 s | pass, 671 s (failed on V41) |
| banner_decoys (negative control) | pass, 711 s | pass, 676 s |

Field matrix: logs/banner_matrix_field2_20261011. Its rows predate the
GROUND-pose 1.5:1 aspect rule and the return-gate placement hint (its ground
row, 913 s, is superseded by banner_ground_aspect15, which has both). The
calm matrix and banner_ground_aspect15 ran the final flight logic. Calm matrix:
logs/banner_matrix_calm1_20261011. Superseded attempts carry STOPPED.md or
were stopped because they imported an older tree; none is counted.

Frozen as V42: .scratch/reduced_scope_v42_candidate_20261011, archive
SHA256 b2c1a5fecff256bb58cd09636f95c2bb2294f1bf01a8287e5ec61f4085b5b45f, 961
files, 41 changed since V41; flown decision modules changed: mission_tree,
banner_node, qr_node, camera_ctrl_node
(logs/reliability_reduced_scope_v42_source_20261011/provenance.json). Full
reduced offline suite on that source: 1809 passed, 8 skipped, all in-scope
checks pass (logs/offline_v42_full_rerun_20261011.log). The first suite run
failed 9 structural tests that read the gate as a direct AlignToBanner child;
they now read the gate selector (logs/offline_v42_full_20261011.log kept).

Rendered, first attempt (logs/banner_rendered_banner_suspended_s20261003_20261011):
GRADE_FAIL at 962.6 s, return gate crossing refused -- the supplied red's
+-25 hue band covered the orange return-lane floor (12 hue steps away), so the
red-zone detector confirmed a restricted zone at the return mouth. Outbound
alignment, corridor, search and delivery (payload error 0.13 m) had completed.
Fixed by colours.separated_ranges (bands stop short of half the hue gap to the
nearest other supplied shade); DIAGNOSIS.md in that directory. The ground run
was stopped before take-off (STOPPED.md). All three are reflown into *_r2.
These rendered runs use the live tree, which after the freeze also gained
the arena-dimensions plumbing (mission_bt main, aggregator, GCS panel) and
the colour separation -- so they are NOT V42 evidence; the next freeze
covers them.

GCS arena dimensions: every dimension the algorithms read (corridor length,
nav height, spacing, banner size and placement, target QR size, payload size,
hall ceiling capping altitudes) is entered at the GCS in m/cm/ft/in,
validated (mission_bt/arena_dimensions.py), applied by rebuilding the
mission tree on the ground only, and reported back as applied. Presets:
two built-in (Simulator arena; SAE Aerothon 2026 clarified) plus operator
presets saved by the aggregator (~/.aerothon/dimension_presets.json). Fields no
algorithm reads yet are recorded and marked so. sim/test_arena_dimensions.py.

Open: issue 43 (ground-only gate approached off-axis squares up on the side
wall); rendered missions for the three placements
(run_banner_placements_rendered_20261011.sh); phase-2 clarification deltas
(QR 1.0 m, one red zone 5 ft, 10 ft / 8 ft heights, payload 10 x 5.5 cm).

# V40 focused contact closure passed; remaining V40 gates running 2026-10-10

Work resumed on the user's instruction. The V39 focused-return contact failure
(issue 42) is resolved on a new frozen source, V40, and repeated into a new
directory. The V39 failure is preserved unchanged, with its original grade,
raw events and missing closure.

V40 archive SHA256 956fadafef24af84b9c047ac87004a273bf14bfebd115def032fdc9a67b3d52e,
951 controlled files. Seven files changed against V39; all 12 flown decision
modules are byte-identical to V39, so no flight behaviour changed. V40 is NOT
an accepted source and the reduced qualification is NOT complete.

Established cause of the 6805 unexpected records, from the preserved evidence
(logs/focused_contact_diagnosis_20261010.json):

1. 6566 skid/payload records were a scene fault. The unloaded fixture drops
   the DetachableJoint, but the world still spawned the cargo under the
   airframe centre, so it fell 2 cm onto the pad against skid_1 before arming.
2. 239 skid/ground records were a grading-contract mismatch. The focused trial
   deliberately lands where the return lane ends, and the contact rule could
   only accept a landing within 1 m of home. Independent truth shows a
   0.49 m/s descent, 0.04 deg tilt, rest from 146.70 s, FCU mode LAND.

No contact occurred above 0.45 m in either group; no hazardous airborne
contact was found, and nothing was reclassified in the V39 record.

Correction: an unloaded fixture parks the cargo 1.2 m from the spawn, and the
focused trial declares its land-in-place from its own onboard FCU pose at the
LAND command. The grader accepts the skids settling on that declared spot only
with fresh truth inside the radius, at or below 0.45 m, at most 1 m/s and
10 deg off level, and fresh FCU LAND mode. The home rule, all seven channels,
the canary, continuous coverage, every other collider and surface, and the
0.70 m / 1.50 m thresholds are unchanged. Accepted landing contacts are
counted, never dropped.

V40 focused repeat, logs/reliability_reduced_v40_focused_split_s20261003_20261010:
seven focused checks pass, minimum corridor clearance 0.730937743964665 m,
connected disarm at 130.785, independent contacts valid with seven channels and
the canary, 0 unexpected records, 141 declared-landing pairs, zero skid/payload
contacts at any time. focused_source_closed_review.json is written.

Running now, in order: five targeted navigation cases reflown on V40, one
complete reduced offline suite, five full rendered acceptances, the 96-flight
reduced campaign at four workers, then the final closure. None of those gates
has passed on V40 yet. Strong gusts and artificially delayed control remain
excluded and unresolved.

## Prior checkpoints

# Stopped by user, executive handoff checkpoint 2026-10-10T16:58:44.085439+05:30

No qualification or mission process is active. The five V39 targeted navigation
cases passed all 13 navigation checks and actually disarmed. The short native
moving-handover return completed all seven geometric/evidence checks at
0.758286655 m clearance and connected disarm. Its separate contact-free closure
FAILED: 6805 unexpected contact records are preserved. No full V39 offline suite,
five full native acceptances, or 96-flight campaign started. V39 remains unaccepted.

Source verification at handoff confirms all 951 controlled files unchanged and
archive SHA256 000dd0834aff203801af9fa8980597634b846ab7806084ed907719478ff2671e.
Strong gusts and artificially delayed control remain unresolved and excluded.
Do not resume automatically. See EXECUTIVE_HANDOFF_20261010.md and
handoff_stop_checkpoint_20261010.json for current state. Older headings below
are chronological checkpoints and may describe work that has since stopped.

## V39 continuous-clearance candidate; qualification active

Source freeze: 951 controlled files; archive SHA256
000dd0834aff203801af9fa8980597634b846ab7806084ed907719478ff2671e. Source remains unaccepted.

The actual native safe-origin scan reproduces an early planner stop
at 0.720 m. Fixed spatial sampling reserves were applied even to
stationary origins and short forecast intervals, then the compiled
shortcut stage repeated the same rejection. V39 uses a continuous
1-Lipschitz distance lower bound and bounded subdivision, with the
unchanged 0.70 m floor and unknown-space checks. The compiled fast
path and 0.025 m grid reserve remain; a failed shortcut batch can
use that same full-clearance certificate. Filtering, thin returns,
normal timing and actuator behaviour remain unchanged.

Six new controls failed before the fix, while four safety negatives
passed. Forty focused checks now pass. The actual normal 0.6 s
airframe hold, with zero added queue, changes from 0.615 m failure
to 0.700267746 m clearance. These are focused sensor/physical seams,
not a completed native mission. All required V39 gates remain.

The original V38 native 17/22 failure is sealed with all artifact
hashes, independent truth, exact archived source, recorded RTL and
actual disarm. The separate overhead-camera demonstration remains
separate configuration evidence. Strong gusts and artificially
delayed control remain unresolved and excluded.

## User-requested bird-eye recording, qualification still paused

A fresh V38 split_corridors.json calm seed 20261003 run was recorded
with an added passive native overhead camera. The flight completed
delivery, full return traversal and actual disarm. Its own grader
reports 22/22, while the previous V38 qualification run remains
17/22 FAILED. Different observation configuration and a private
provenance adapter are documented; this demonstration is not used
to resume or complete qualification. Both records remain preserved.
The overhead capture contains 1501 frames with zero drops; the
export contains 1340 frames at original capture intervals, 446.22
seconds, including confirmed disarm. Full-speed and 4x MP4 exports
decode successfully. Source hashes verify all 949 files unchanged.
The post-disarm native contact-recorder GIL shutdown abort remains
preserved and unresolved. Two unarmed setup attempts are retained.
Closed recording proof: logs/user_birdseye_split_v38_s20261003_retry3_20261009/birds_eye_recording_closed_review.json

## Qualification paused by user; custom-world recording supplied

Current V38 split_corridors.json, calm seed 20261003 completed recording
through actual disarm. Video decode passed; simulation-time export
duration is 471.201 seconds. Delivery was confirmed. The run FAILED
17/22 acceptance checks: return became STUCK and independent clearance
fell to 0.6949338146612648 m, below unchanged 0.70 m. Safe operator RTL
returned home and disarmed; associated mode, ceiling and incomplete
return checks remain failed. Original records and stop receipt retained.
No remaining native runs or campaign were started. Source is unaccepted.
Record: logs/reliability_reduced_v38_render_split_corridors_s20261003_20261008/user_recording_delivery_checkpoint.json

## V38 targeted navigation verified

All five exact-source cases passed all 13 navigation checks, with actual
connected disarm, zero contacts/fence breaches and verified source/archive
hashes. Normal actuator response 0.6 s, zero additional transport queue,
camera 20 Hz/lidar 10 Hz, 0.20 s computation budget and RTF1 are retained.
The table is navigation-only evidence. Rendered perception and motor delivery
were not exercised. Random seed 4 retains DEGRADED landing quality.

| Preset | Seed | Corridor metres | Red metres | Airborne seconds |
|---|---:|---:|---:|---:|
| random | 3 | 0.745196781 | 2.262071264 | 823.8 |
| field | 1 | 0.728426487 | 2.368071264 | 643.2 |
| field | 2 | 0.739602153 | 2.305071264 | 634.8 |
| field | 3 | 0.750233138 | 2.319071264 | 654.6 |
| random | 4 | 0.730813181 | 2.015071264 | 657.0 |

The complete reduced offline suite PASSED: 1697 tests passed, eight
skipped (five deferred strong-gust tests, three empty photograph-corpus
tests). Syntax, configuration parsing and the frontend build also pass.
Source closure verifies all 949 controlled files unchanged. The first
rendered split-course acceptance is active; all five final native 22/22
acceptances and 96 eligible campaign flights remain unqualified. No
source is accepted yet and no original 200-case qualification is claimed.

# Current checkpoint: V38 provisional, complete offline integration correction

V38 freezes 949 controlled files, archive SHA256
eb38b8d828445196fa6716461bd42f66c94ce90fb4b72b696d22b40129f2d213. 152 integrated focused checks pass.
The camera settlement stage now has its normal CAMERA_BANNER UI state.
Flight-logic AST is unchanged after excluding only STATE_NAMES. Seven
stationary-hold fixtures previously placed their expected stopped poses
inside the observed 1.50 m red margin. The toy boundary now puts those
stops outside that unchanged margin; the requested trip still crosses
red. Every original assertion is retained. Two additional actual-command
controls require an inside-margin stop to keep escaping and require
distinct fresh captures after actual certified escape arrival. Existing
observed-exclusion, actual gate/vertical physics, camera handoff, stale
motion, braking, landing and scan-registration regressions also pass.
No world geometry, filtering, acceptance threshold or flight policy changed.

V37's five navigation passes remain archived on their original source.
Its complete reduced offline suite FAILED eight checks: one UI-state
mapping and seven invalid stationary-hold fixtures; 1687 passed, eight
skipped, with syntax/configuration and frontend checks passing. The exact
source, failure names, complete log and hashes are preserved in
failed_full_offline_closed_review.json. They are not counted as V38 passes.
No native acceptance or campaign ran on V37.

V38 runs all five targeted flights again on the final source and exact
RTF1 configuration, then one complete reduced-scope offline suite, five
native 22/22 acceptances and 96 eligible campaign flights. Strong gusts and
artificial delayed control remain unresolved and excluded. No source is
accepted yet, and no original 200-case qualification is claimed.

## V37 completed verification result

All five exact-source normal-timing navigation cases passed all 13 checks,
with actual disarm and zero contacts/fence breaches. The complete reduced
offline suite then FAILED: 8 failed, 1687 passed, 8 skipped, 3158.98 seconds.
Python/shell syntax, XML/YAML parsing and the frontend build passed. One
failure is a missing UI state for CameraBannerReturnAlignment. Seven
search-hold fixtures expect completion while still inside the observed
1.50 m exclusion margin; their interaction with the stricter escape policy
requires correction and validation. No threshold or assertion has been
waived. The source, completed failed log, exclusion ledger and exact
failure names are preserved in failed_full_offline_closed_review.json.
No native acceptance or campaign ran, and V37 is not an accepted source.

# Current checkpoint: V37 provisional, exact-clock guard and real-time flights

V37 freezes 949 controlled files, archive SHA256
de2a300afd15027061feebdba752efb8c0ab294041bfbd471a96cf5cd59722fb. 107 integrated focused checks pass.
The recorded 682.02 to 682.32 capture interval reproduces a false gate
history-gap rejection from floating-point subtraction. The gap comparison
now uses the ROS clock's integer nanosecond precision: exactly 300000000 ns
is accepted, 300000001 ns is rejected at three different clock epochs.
The 0.30 s threshold is unchanged. Specific vector-history faults are now
recorded in gate failure reasons. Prior gate braking, camera handoff,
search braking, scan registration and physical altitude fixes are retained.

V36 safely closed two failed mild-weather flights; three queued field cases
were never flown. Random 4 failed its gate motion guard, then contacted
the board during abort and eventually disarmed. Random 3 experienced
computation-deadline misses and a genuine vertical-motion capture gap;
it stopped in return corridor, exceeded 900 s, then returned on battery
abort and actually disarmed. The operator stop watchdog subprocess timed
out after 15 host seconds and terminated; this limitation is retained in
the pipeline log. No older failure is excluded or upgraded to a pass.
The recordings demonstrate delayed arrivals on this accelerated host run;
they do not establish a callback race or prove the numerical boundary was
the sole cause of the actual gate failure. Immutable source/configuration,
every failed grade, contact and actual disarm are in the closed review.
No complete offline, native or campaign qualification ran on V36.

V37 object flights use real-time simulation speed, RTF 1, with two workers.
Controller and sensor rates in simulated time, the 0.20 s computation
budget, 0.6 s normal actuator response, zero additional transport queue and
all acceptance thresholds remain unchanged. This reduces host work per
second without adding control delay. Targeted and campaign verifiers
require this exact configuration. The watchdog records timeout attempts
and retries instead of exiting and leaving later stop requests unhandled.

All five normal-timing targeted passes, the complete reduced-scope offline
suite, five native 22/22 acceptances and 96 eligible campaign flights remain
required on the final source. Strong gusts and artificial delayed control
remain unresolved and excluded. No accepted source or original 200-case
qualification is claimed.

# Current checkpoint: V36 provisional, physical corridor altitude hold verification

V36 freezes 949 controlled files, archive SHA256
7a0e5214e6f25a3180c8ff4e10f79731074e55b8584d34db7634794a85d65dc2. 98 integrated focused checks pass.
The V35 captured barometer errors replay the corridor dip through the actual
published vertical command and unchanged normal airframe: minimum 0.274 m,
below the unchanged 0.30 m airborne floor. With constant barometer errors
the same control passes. Half gain also passes that trace but retains
estimator-driven physical motion; it was not adopted. The new hold uses
signed FCU vertical displacement from the actual control handover while
retaining the commanded altitude offset, original 0.8 gain and 0.6 m/s cap.
The replay minimum becomes 0.784 m. Distinct captures integrate actual
motion; duplicate captures and repeated unchanged target messages cannot
reset the hold. Invalid or discontinuous motion fails closed until an
actual new handover. True sink, target changes, stale/missing/future/nonfinite
captures, disabling and re-enabling controls pass. This isolated vertical
replay is diagnostic evidence; horizontal flight and native delivery are
not exercised by it. No geometric truth or venue configuration is a
production input; lidar filtering and all acceptance limits are unchanged.

V35 safely closed five trials. Field 1/2/3 and mild random 3 passed all
13 navigation checks. Mild random 3 retained 0.7424024489799385 m corridor
clearance and 2.204071263555253 m red clearance, with actual precise disarm.
Mild random 4 failed return traversal when true altitude dipped below 0.30 m
for eight samples despite 0.7339558114779715 m wall clearance. Zero contacts
and fence breaches, actual disarm and DEGRADED landing are retained.
The old failed grade remains failed. No complete offline, native or campaign
qualification ran on V35.

V36 runs mild random 4/3 first, then field 2/1/3 with normal actuator
response and zero added queue. Five exact-source navigation passes remain
required before the complete reduced-scope offline suite, five native
22/22 acceptances and 96 eligible campaign flights. Strong gusts and
artificial delayed control remain unresolved and excluded. No accepted
source or original 200-case qualification is claimed.

# Current checkpoint: V35 provisional, gate physical braking hold verification

V35 freezes 946 controlled files, archive SHA256
b97b74647bb4531e0b7f359d9653e726ab4276e7c0045bf19844c1dfd0aaa510. 66 integrated focused checks pass.
The existing recorded entry replay retains 0.913 m clearance; the new
recorded braking seam changes from 0.668 m failure to 0.986 m pass with
normal 0.6 s actuator response and zero additional control queue. A fixed
estimated XY hold chased GPS changes. The new estimated-frame anchor
cancels those changes while preserving the physical arrival from distinct
continuous FCU ground velocities. Missing, malformed, nonfinite, future or
gapped vectors fail closed. Duplicate captures cannot finish braking.
Pending speed acknowledgement remains a physical hold. Altitude, freshness,
speed, settling and clearance thresholds and the lidar filter are unchanged.
These replays regenerate wind and lidar; they are diagnostic evidence,
not reconstructed ROS scheduling or rendered qualification.

V34 safely closed three trials: field seeds 2 and 3 passed navigation and
landed precisely; mild random seed 3 failed only corridor clearance at
0.6560762476749438 m, with zero contacts/fence breaches and actual disarm.
The minimum occurred during gate crossing/braking before the corridor
velocity controller was enabled. The full old failure, source, configuration
and telemetry hashes are preserved. Two queued flights were cancelled
before flight. No offline, native or campaign qualification ran on V34.

V35 runs mild random 3 first alongside field 3, then field 2/1 and mild
random 4. Five exact-source navigation passes are required before the
complete reduced-scope offline suite, five native 22/22 acceptances and
96 eligible campaign flights. Strong gusts and artificial delayed control
remain unresolved and excluded; no original 200-case qualification or
accepted final source is claimed.

# Current checkpoint: V34 provisional, return camera handoff verification

V34 freezes 944 controlled files, archive SHA256
34aad95e05f1fface7dd8b931892fb1d909d86e7004d2b7af554e2cc694dbd15. 59 focused normal-startup camera,
framing, gate-motion, corridor registration and return-climb checks pass.
The actual built return handoff went RED at the inherited -10 degree search
tilt before the change. It now restores BANNER and waits for measured camera
settlement before alignment. Existing timeout and low-view level-camera
retry remain unchanged. Stale readback, wrong measured angle and timeout
controls pass. No movement is authorized by camera framing.

V33 safely closed five targeted trials: four navigation passes, one failure.
Field seed 3 found the delivery QR and return gate, then failed alignment
after seven vantages. A custom camera tilt from distant search remained
active after the approach; subsequent clipped/missing lettering led to
230 seconds of alignment and eventual safe return. The actual connected
disarm, failure grade, zero contacts/fence breaches, source archive,
configurations and every recording/telemetry hash are retained in the closed
review. Field 1/2 and mild random 3/4 passed navigation. Random 4 retains
DEGRADED landing quality. No offline, native or campaign ran on V33.

Field 3 reruns first in parallel with mild random 3. All five exact-source
targeted passes remain required before the complete reduced-scope offline
suite, five native 22/22 acceptances and 96 eligible campaign flights.
The five strong-gust positive offline flight tests remain explicitly
excluded, with their original V32 failures preserved. Three empty photograph
corpus checks remain skipped. Neither exclusion counts as a pass.
Strong gusts and artificially delayed control remain unresolved/excluded.
The reduced campaign has 120 selected entries, 80 weather exclusions and
24 negative geometry classifications. No accepted source or original
200-case qualification is claimed. Thin obstacles and all acceptance
thresholds remain unchanged.

# Current checkpoint: V33 provisional, explicit reduced offline scope

V33 freezes 943 controlled files, archive SHA256
6998503b93f268a808b75e1108d34dd52e09d37102c373c6e64b46747f6b96f2. All 121 combined focused checks pass.
Controller and perception source bytes are unchanged from V32. The changes
are the QR regression's hazard cadence and explicit offline scope/reporting.
Its original assertions remain: at least six replans, zero skipped lanes and
coverage of every clear lane part. The actual pytest collection checks prove
that five strong-gust positive flight tests are excluded while dirty lidar,
slow-airframe checks and the negative wind-fixture guard remain included.
Default offline runs still collect and execute every test without exclusions.

V32 passed all five targeted navigation cases, including field seeds 1/2/3,
with zero contacts/fence breaches and actual connected disarm. Random seed 4
retains DEGRADED visual-landing quality. Its exhaustive offline attempt was
interrupted for diagnosis: five failures and 1085 passes before interruption.
Four failures use mean wind 8 m/s, gust 4 m/s and are unresolved/deferred.
The fifth was the QR regression fixture timing. Python/shell syntax, config
parsing and frontend build passed. The original interrupted log, exact grades,
source archive, recordings and disarms are retained. No native or campaign
was executed on V32. No exhaustive offline pass is claimed.

Five targeted cases now rerun against the complete V33 freeze. The complete
reduced-scope offline suite follows, with five strong-gust flight tests
explicitly skipped and recorded, plus the three empty photograph corpus
skips. Neither exclusion is a pass. Five native 22/22 acceptances and the
96 eligible campaign flights remain pending. No accepted source exists.
Strong gusts and artificially delayed control remain unresolved and excluded.
The campaign retains 120 selected entries, 80 weather exclusions and 24
negative geometry classifications. No original 200-case qualification is
claimed. Acceptance thresholds and thin obstacles remain unchanged.

# Current checkpoint: V32 targeted navigation passed; final qualification pending

All five exact-source targeted cases passed all 13 navigation checks,
with zero contacts/fence breaches and independently recorded connected
actual disarm. Field seeds 1, 2 and 3 and mild random seeds 3 and 4 passed.
Native perception and motor delivery remain unqualified. Random seed 4
retains its DEGRADED visual-landing label; it is not upgraded to PRECISE.

| Conditions | Seed | Corridor m | Restricted-zone m | Airborne s |
|---|---:|---:|---:|---:|
| random | 3 | 0.7406553573819102 | 2.2310712635552505 | 792.1 |
| field | 1 | 0.7397704722994515 | 2.233071263555253 | 667.4 |
| field | 2 | 0.7324389980934507 | 2.1670712635552505 | 688.4 |
| field | 3 | 0.7445042161212453 | 2.3400712635552523 | 709.4 |
| random | 4 | 0.7384869906322743 | 2.0360712635552503 | 772.7 |

The one final offline suite is next, followed by five exact-source native
22/22 acceptances and 96 eligible campaign flights. Strong gusts and
artificially delayed control remain unresolved and excluded; original
failures remain unchanged. No reduced qualification completion or
original 200-case qualification is claimed.

# Current checkpoint: V32 provisional, hazard-hold verification active

V32 freezes 941 controlled files, archive SHA256
853b371de0ab27472d5f88a272df1703cd6e0bf5dedfceab81513adb3b70a767. All 99 focused checks pass, covering search-anchor
revalidation, unknown or stale motion, obstructed escape, distinct stopping
captures, corridor registration, gate motion and visual landing capture gaps.
Normal startup resolves all 11 decision/perception modules to this freeze.

V31 safely closed three targeted navigation trials. Field seeds 2 and 3 passed
all 13 navigation checks and actually disarmed with PRECISE landing. Mild
random seed 3 passed corridor clearance (.7372377792461882 m), return, time
and actual disarm, but FAILED restricted-zone clearance at 1.2139113263915782
m against the unchanged 1.50 m requirement. All three had zero contacts and
fence breaches; two unflown trials were cancelled. These headless trials do
not qualify rendered perception or motor delivery. Original grades, source,
configurations, recordings and disarms remain in the closed failure review.

The failed minimum occurred during QR search while the controller repeatedly
held an anchor newly covered by observed restricted-zone paint. The actual
search-braking seam failed before the fix. V32 revalidates both active and
completed stationary anchors against current observed exclusions, requires
fresh measured motion, and uses the existing router to certify the nearest
edge escape. If new paint blocks that escape, it latches a fresh stationary
position. It cannot finish escape while inside the original safety margin.
Acceptance thresholds, thin obstacles, filters, actuator response and timing
are unchanged. Whole-flight restricted-zone clearance remains unverified.

Five exact-source targeted cases rerun before one final offline suite, five
native rendered 22/22 acceptances and the 96 eligible campaign flights.
No accepted source exists. Strong gusts and artificially delayed control
remain unresolved, preserved and excluded. The reduced matrix has 120
selected entries, 80 weather exclusions and 24 negative geometry
classifications; those negative entries are not passes. No original
200-case qualification is claimed.

# Current checkpoint: V31 provisional, scan-motion verification active

V31 freezes 940 controlled files, archive SHA256
8ef5b87efad7833eae8f358b418f00ab6ed2bea31ff668d80ead715197841b25. 51 focused capture/controller/landing/gate checks pass;
80 further controller, scan geometry, velocity timing and command regressions
pass. These batches overlap and are not summed as unique tests.

V30 closed three targeted trials. Field seeds 2 and 3 passed all navigation
checks and actually disarmed with PRECISE visual landing quality. Landing took
about 24 seconds on each. Mild random seed 3 landed and disarmed within the
900-second limit, but failed corridor clearance at .6908234714203971 m.
All three had zero contacts and zero fence breaches. Two unflown cases were
cancelled. Original grades, source hashes and actual disarms are retained in
the exact-source closed review. No offline suite, native or campaign was run.

At the failed clearance minimum, recorded observed clearance .7289959824800055
m exceeded independently measured truth .6908234714203971 m by about 38 mm.
Subscription timing prevents treating the two captures as exactly simultaneous.
The actual scan registration and packet/normal-airframe regression reproduces
clearance .6920706531937814 m when stationary ground velocity is accompanied
by 40 mm GPS position jitter. Scan alignment previously treated that GPS jitter
as short aircraft displacement, shifting obstacle points away from the aircraft.

V31 uses distinct fresh FCU world ground-velocity captures to integrate the
short displacement between scan capture and current pose. Broken, stale or
uncovered histories fail closed; at most .06 s of last-sample continuation is
allowed for normal pose/velocity callback skew. Capture orientation, relative
sensor mount, all original ranges, thin obstacles, filters, motion budget,
actuator response and acceptance thresholds remain unchanged. Existing paired
pose fallback is retained when no FCU velocity stream exists.

The actual registration/packet regression went RED before this fix and GREEN
after it. The recorded-entry corridor replay reaches 10.34 m progress in 22.5
s, .72650807605208 m minimum clearance, zero contacts. It regenerates lidar
and does not reconstruct ROS callback ordering or qualify a whole mission.
The earlier 50 mm reserve prototype fixed the narrow range-error seam but got
stuck in the recorded corridor at 2.93 m progress. It was rejected and was
never integrated into production.

Five targeted cases now rerun. All five passes are required before one final
offline suite, five rendered 22/22 acceptances and 96 eligible campaign flights.
No accepted source exists. Strong gusts and artificially delayed control remain
unresolved, preserved and excluded. The reduced matrix retains 120 selected
entries, 80 weather exclusions and 24 negative geometry classifications.
No original 200-case qualification is claimed.

# Current checkpoint: V30 provisional, targeted verification active

V30 freezes 939 controlled files. Archive SHA256
dfdc35d4be06d18e8871cde00147b3ff2b846af93decff25fdb74373a1701696. The change retains the latest visual horizontal
landing correction during the existing brief-loss grace period while holding
current height. Prolonged loss still invokes the original recovery; no descent
continues without visual lock. The actual descent regression went RED before
the fix; 52 focused checks passed after it. The simplified 10.79-second landing
physics replay does not reproduce the full failure and is not whole-flight
evidence. All previous failures and all acceptance thresholds remain intact.

Five targeted cases now run on this source with normal actuator behaviour and
zero injected delay. Only five passes unlock one final offline suite, five
full rendered acceptances, and the 96 eligible campaign flights. No accepted
source exists. Strong gusts and artificially delayed control remain unresolved,
preserved and excluded. No original 200-case qualification is claimed.

# Current checkpoint: V29 closed, timing failures unresolved

V29 executed three of five planned targeted navigation trials. Field seed 2
passed all navigation checks and actually disarmed at 776.60 s, with DEGRADED
visual landing quality. Mild random seed 3 and field seed 3 failed the
unchanged 900-second limit; both safely returned and actually disarmed.
All three recorded zero obstacle contacts and zero geofence breaches. Mild
seed 3 passed both corridors with .7230623482323127 m minimum clearance.
Two unflown trials were cancelled, never counted as passes. The original
failed results and all telemetry remain archived. No full suite, rendered
acceptance or campaign was run on V29. No accepted source exists.

Landing diagnosis is active. A simplified free-airframe replay finished in
10.79 s and does not reproduce the full timing failure. Replaying recorded
aircraft positions reproduces the long camera outage but cannot verify a
counterfactual controller change. A separate actual PrecisionDescent regression
does reproduce early climb toward the stale initial home-marker fix after
one missing camera result, before the existing loss grace expires. The first
candidate correction retains the latest visual horizontal target during
that existing grace while holding current height. It does not continue
descent without lock or change the prolonged-loss recovery, timeout or any
acceptance threshold. Whole-flight verification is required before adoption.

Strong-gust and artificially delayed-control failures remain unresolved,
preserved and excluded. Reduced scope remains 120 weather-selected cases,
80 weather exclusions and 24 negative geometry classifications, leaving 96
eligible campaign flights. None has qualified; original 200-case qualification
is not claimed.

# Current checkpoint: V29 provisional

No accepted source. V29 freezes 938 controlled files, archive SHA256
a65281dcfbb00b3203bf8a1ee069dfc7633c59d793c4db2c6e31519c86c7be66. All 11 normal-startup module hashes match.
91 focused checks pass, including the actual gate leaf, normal actuator
airframe, streamed lidar keep-out guard and frozen failing observation stream.

V28 closed three trials: field seeds 2 and 3 passed all navigation checks and
actually disarmed. Field 2 retained DEGRADED visual landing quality. Mild
random 3 found its return gate in 15.15 s, versus V27's 187.64 s, but later
timed out at GateAdvance. It recorded two wall contacts and .4034108728140693 m
minimum corridor clearance. Automatic RTL and actual connected disarm were
recorded; the original failed grade is preserved. Two unflown cases were
cancelled, never counted as passes. Its exact-source closed failure review,
recorded setpoints, estimate/truth alignment and original sensor data remain
archived. The contacts occurred during crossing, before the braking phase;
the late phase label did not establish a braking root cause.

The actual gate replay reproduced timeout, wall contact and .4003839764804563 m
clearance with normal .6 s response and zero transport queue. Changing only
the settle-position window did not fix it. Damping the original braking
anchor with measured velocity also did not fix it; neither prototype was
adopted. The successful change confirms signed forward crossing distance
from distinct fresh FCU world-frame ground-velocity captures since speed
admission. It retains the original measured distance, latched heading,
arrival tolerance, fresh pose/velocity/lidar requirements, .08 m/s braking
limit, three distinct braking samples, .3 s settling span and speed ACKs.
Duplicate, pre-admission, backward, sideways, stale, nonfinite and broken
capture histories cannot supply this extra arrival confirmation. The
existing position arrival path and latched streamed setpoint are retained.

The permanent replay regression went RED before the fix and GREEN after it:
crossing/braking completed in 20.8 s, minimum clearance .9145067912135068 m,
zero contact, normal physics. This is a focused diagnostic regression with
recorded estimator error and regenerated scan noise, not rendered or whole
mission qualification. No production node reads the evaluation fixture.

V29 now reruns five exact-source targeted cases, beginning with mild random 3
and field 2. Only all five passes unlock one final offline suite, five native
22/22 acceptance runs and 96 eligible campaign flights. Reduced scope remains
120 selected, 80 weather exclusions and 24 negative geometry classifications.
No campaign flight has qualified. Strong gusts and artificially delayed
control remain unresolved, preserved and excluded. No original 200-case
qualification is claimed. All acceptance limits and thin-obstacle filtering
remain unchanged.

# Current checkpoint: V28 provisional

No accepted source. V28 freezes 935 controlled files, archive SHA256
20ac779c2748d870980b75fd95f7b159ad2341f05d0abe8d3d1442b8ec7188ef. All 11 normal-startup imports match. The return-camera
restart seam and 92 related focused checks pass.

V26 closed with four navigation passes and one failure. Field seeds 1, 2 and 3
and mild random 4 passed navigation and actually disarmed. Mild random 3
failed the high-return altitude handover; automatic RTL and actual disarm
were retained. V27 closed with field seed 2 navigation PASS, corridor minimum
.7354888194818544 m and actual disarm. Mild random 3 found its delivery QR,
completed the stricter climb and entered return search. Search took 187.64 s;
the flight exceeded the unchanged 900 s limit before completing the return.
The safety watcher requested RTL, and actual connected disarm was recorded.
Zero contact and fence events were recorded in both closed V27 trials.
Three unflown cases were cancelled, never counted as passes. Both candidates'
original grades, configurations, source archives and complete file hashes
are retained in their targeted_failure_closed_review.json files.

The actual FindReturnBanner state machine reproduced a missed first orbit
view carrying its final BANNER camera tilt and exhausted second-look flag
into later orbit vantages. V28 starts each orbit vantage at FORWARD, resets
its second BANNER look, and starts a fresh heading dwell. The existing orbit
altitude, bounded speed, fence/red-ground/lidar guards and identity/range
checks remain unchanged. Captured-geometry projection showed readable level
views at later recorded orbit positions, while a 2 m raise did not repair
the early incidence-limited view. These are diagnostic replays, not rendered
qualification or a reconstruction of every runtime detector callback.

The initial focused fixture lacked the speed acknowledgement stub; that
fixture was corrected without changing production speed behavior. A premature
V28 freeze is retained under the explicitly named preverification directories;
it ran no flights and cannot qualify. The final V28 freeze is the hash above.

Five same-source targeted passes still gate one final offline suite, five
native 22/22 rendered acceptances, and 96 eligible campaign flights. The exact
reduced matrix remains 120 selected cases, 80 weather exclusions, and 24
negative geometry classifications. No campaign flight has qualified. Strong
gust and artificially delayed-control failures remain unresolved and excluded.
No original 200-case qualification is claimed. V28 retains the strict return
climb and zero-disturbance certificate; all .70 m corridor and other required
acceptance limits remain unchanged.

# Current checkpoint: V27 provisional

No accepted source. V27 freezes 934 controlled files, archive SHA256
a4291e9f8f93b0b98d008b6be6f9182a8090f8eae0b37bc2058fa6af3adb7fda.
All 11 normal-startup imports match; 226 focused checks pass. The actual
built mission reproduced the return handover failure at measured altitudes
9.41, 9.50 and 9.69 m: ClimbForReturn inherited a .60 m tolerance, while
RestoreNavigationSpeed correctly requires at least 9.70 m for a 10 m transit.
V27 finishes this particular climb within .20 m, retaining the following
.30 m guard, fresh pose, nadir settlement, acknowledgement and bounded cap.
The climb continues commanding 10 m without restoring horizontal speed early.
Other climb tolerances, target height and acceptance thresholds are unchanged.

V26 field 2 passed navigation with .7318246284671641 m minimum corridor
clearance and actual disarm. Mild random 3 found the delivery QR, but failed
at the high-return handover before return search. The original failed grade,
fresh-pose diagnosis, automatic RTL and actual disarm are preserved. The
remaining isolated V26 flights continue to close; none can qualify V27.

V27 starts its priority mild seed 3 on the already closed V26 domain 41.
Its second worker waits until the entire V26 batch closes before reusing
domain 40, maintaining at most two active flights across both candidates.
Five same-source navigation passes are still required. A failed V27 case
stops queueing unflown cases; already armed flights finish safely and retain
telemetry through actual disarm. Cancelled unflown cases are not passes.

Only five V27 targeted passes unlock one final offline suite, five full native
22/22 rendered acceptances and 96 eligible campaign flights. Reduced scope
remains 120 selected, 24 negative geometry classifications and 80 weather
exclusions. No campaign flight has qualified. Strong-gust and artificially
delayed-control failures remain unresolved and excluded. Original 200-case
qualification is not claimed. V26's conservative zero-queue certificate and
side-to-vertical framing fix are retained; no .70 m clearance or thin-obstacle
filter has been weakened.

# Current checkpoint: V26 provisional

No accepted source. V26 freezes 933 controlled files, archive SHA256
5060d02d8a7ccdf8abb852bd405651ba90231135ceb975d68e7102fad9b9fb6e.
All 11 normal-startup imports match. 122 integrated focused checks and 24
normal navigation/timing checks pass. Two actual decision seams reproduced
defects before their respective fixes:

* FindReturnBanner used one retry key for both a side crop and the horizontally
  centred vertical crop at the same vantage/tilt. Centring consumed the later
  vertical recovery. V26 includes horizontal completeness in the key. Each
  framing class still receives only one retry after distinct fresh captures;
  camera settlement and the three-adjustment tilt bound remain required.
  Clipped range remains unusable and cannot authorize gate crossing.
* The actual motion certificate skipped its zero-disturbance prediction when
  transport queue was zero. A modest .06 m/s helpful response error authorized
  a packet whose actual .6 s response/braking tail reduced clearance to
  0.6990529898953362 m. The frozen V25 publication method reproduces this with
  the normal .20 s computation budget. V26 requires both predictions even with
  zero queue. A prior narrow (.85 m) forecast test now checks refusal rather
  than authorizing a packet safe only if the estimated disturbance occurs.
  A separate wider case proves forecast compensation remains available when
  both predictions preserve the same .70 m minimum. No threshold was reduced.

V25 closed four navigation passes. Fields 1/2/3 and mild random 4 completed
and actually disarmed. Mild random 3 found its delivery QR but spent 190.85 s
in return-gate search; it failed time/unexpected mode and actual corridor
clearance 0.6849396857248734 m. Watchdog RTL was requested only after the
unchanged 900 s airborne limit; recording continued through actual disarm.
All five closed with zero contacts/fence breaches. Mild random 4 reported
DEGRADED precision, retained as a quality limitation. The exact-source closed
review preserves every failed grade and artifact. Fixture delivery remains
unmeasured and unqualified. No full offline suite was run on failed V25.

Five V26 two-worker targeted trials are active with normal .6 s response,
20 Hz camera/10 Hz lidar, .20 s computation budget and zero artificial queue.
Only five same-source navigation passes unlock one final offline suite, then
five native 22/22 rendered acceptances and 96 eligible campaign flights.
Reduced scope is 120 selected, 24 negative geometry classifications and 80
weather exclusions. No campaign flight has qualified. Strong-gust and
artificially delayed-control failures remain unresolved and excluded.
Original 200-case qualification is not claimed.

Isolated V24 corridor probes are diagnostic only. Full-entry regenerated-noise,
normal-computation and full-attitude variants passed; 12 other normal lidar
realizations also passed. Starting from the recorded near-boundary state
reproduced a .69172 m deficit, but does not prove what caused the approach.
The coherent .04 m outward-bias probe also passed and its original filename
containing "red" does not make it a reproduced failure. All diagnostic verdicts
are preserved; none replaces full-flight or native acceptance. The new modest
response-error seam proves a certificate gap, not exact causation of every
older runtime failure. Final source qualification remains required.

# Current checkpoint: V25 provisional

No accepted source. V25 freezes 931 controlled files, archive SHA256
97bb0330beb893151c3e94632ec013d560201ec5f6a594bf18cbb6359e5a1108.
All 11 normal-startup imports match; 297 focused checks pass. The actual
AlignToBanner transit reproduced a premature cancellation of the requested
2 m camera framing backoff: a still-clipped identified view passed the legacy
near-view shortcut before the backoff completed. V25 requires a complete view
for that shortcut. It preserves the existing complete near-board stop and
the bounded backoff, gate braking, perception and camera capture scheduling.

V24 closed with four of five navigation passes. Field seeds 1/2/3 and mild
random 4 passed navigation and actually disarmed with zero contacts/fence
breaches. Mild random 3 also completed and actually disarmed, but its actual
minimum corridor clearance was 0.6948520402727778 m, below the unchanged
0.70 m requirement. Airborne time was 792.1 s. This original failed grade,
source/configuration and all artifacts are preserved in the closed review.
Mild random 4's DEGRADED landing is retained as a quality limitation. Fixture
delivery is unmeasured and does not qualify motor delivery.

V25 same-source targeted trials are active with two workers, normal .6 s
actuator response, native-matching 20 Hz camera/10 Hz lidar, .20 s computation
budget and no injected transport queue. Five navigation passes are required
before one final offline suite, five full native 22/22 rendered acceptances
and 96 eligible campaign flights. No campaign flight has yet qualified.
Reduced scope remains 120 selected, 24 negative geometry classifications and
80 weather exclusions. Strong-gust and artificial delayed-control failures
remain unresolved and excluded. Original 200-case qualification is not claimed.

The V24 clearance minimum occurred in RETURN_CORRIDOR near obstacle 1.
At that sample the controller was BLOCKED, published zero horizontal velocity,
and reported no certified braking clearance. Measured lidar clearance was
0.70830 m while independent truth was 0.69485 m. Two isolated actual-controller
and normal-aircraft probes passed, at 0.72785 and 0.73045 m respectively. They
regenerated lidar streams and omit live ROS ordering, so neither reproduces
the runtime failure or qualifies a source. No speculative clearance change
has been made.

# Current checkpoint: V24 provisional

No accepted source. V24 freezes 930 controlled files, archive SHA256
c99e3bb6fb4dcbb0f74a0cb90dc3ffe13a9122cd8897fb75e6e21f9ae052b491.
All 11 normal-startup imports match; 314 focused checks pass. The actual search
leaf reproduced a camera-only framing deadlock: the same identified board was
cut off at the bottom with FORWARD and at the top with BANNER, and the recovery
oscillated between the two. V24 brackets opposing fresh vertical crops from the
same held view and commands an intermediate angle using camera_ctrl's existing
numeric-degree protocol. It allows at most three adjustments within the existing
0 to -20 degree range. Numeric requests must match the measured camera controller
readback and settled/fresh state. Duplicate, stale, unidentified, unsettled,
moved-view, changed-bearing, side-crop and exhausted cases refuse the bracket.

Framing moves only the camera. Clipped images still cannot provide accepted
range, identity acceptance or crossing permission. Body translation, altitude,
search pacing, the .30 s trust age/.08 m/s braking checks, .70 m corridor and
1.50 m red clearance, 900 s time limit, sensor schedules, lidar filters and
actuator response are unchanged from V23.

Five two-worker V24 same-source targeted navigation trials are active. They
must all pass before one final offline suite, five full native rendered
acceptances and 96 eligible campaign flights. Reduced scope remains 120
selected, 24 negative geometry classifications and 80 weather exclusions.
Strong gusts and artificial control delay remain unresolved and excluded.
Original 200-case qualification is not claimed.

## V23 closed result

V23 fields 1/2 and mild random 4 passed navigation. Field 3 and mild random 3
failed time/unexpected mode; mild random 3 also failed return. All five actually
disarmed with zero contacts/fence breaches. Their original grades are preserved
in the exact-source per-artifact closed review. Mild random 4 reported DEGRADED
precision, retained as a quality limitation. Fixture motor delivery remains
unmeasured and unqualified. No full offline suite was run on failed V23.

High return transit measured 11.04 s for field 2 and 11.46 s for mild random 3,
versus 70.64 s in the retained V22 mild failure. The acknowledged speed lease
release is integrated and retained in V24. Remaining return searches were slow:
field 3 spent 194.96 s before alignment, while mild random 3 remained searching
through watchdog return. Passive snapshots show the opposing crop pattern;
they are not a complete 20 Hz banner ledger and do not prove an exact runtime
capture streak. The large level top-crop hypothesis had zero matching observed
examples and was not adopted. The real leaf's opposing-tilt red and focused
green results drive V24 instead.

# Current checkpoint: V23 provisional

No accepted source. V23 freezes 928 controlled files, archive SHA256
8b4af0bcf992a1b55ea4c55114d8cca1effd4d5e96e3154e0c3fbcaa67bb904c.
All 11 normal-startup imports match; 272 focused checks pass. The actual normal
mission sequence failed the regression: a .65 m/s admitted search cap persisted
into the high return transit. Retained V22 mild seed 3 measurements show the
same pattern with a .60 m/s cap: 41.70 m horizontal travel took 70.64 seconds,
mean .590 m/s and median recorded velocity .600 m/s.

V23 records the previously admitted navigation cap before search. Only after
delivery, return climb and confirmed nadir camera, a new stage holds position
until the FCU acknowledges restoration bounded by that previous cap and the
existing configured navigation ceiling. Fresh pose, high altitude and camera
prerequisites are mandatory. Rejection, unavailable service and timeout fail
safely. Search pacing, .30 s capture freshness, .08 m/s braking, all acceptance
thresholds, sensors, lidar filtering and actuator physics remain unchanged.

V22 is closed: all five actually disarmed; fields 1/2/3 and mild random 4
passed navigation, while mild random 3 retained its time/return failure.
V23 five two-worker same-source targeted trials are active and must pass
before one final offline suite, five
full native rendered acceptances and 96 eligible campaign flights. Reduced
scope remains 120 selected, 24 negative geometry classifications and 80 weather
exclusions. Strong gusts and artificial control delay remain unresolved and
excluded. Original 200-case qualification is not claimed.

V22 fields 1, 2 and 3 have completed and actually disarmed. Field seed 2 passed
all navigation checks with precise landing, .730684650 m corridor clearance,
757.4 airborne seconds and .32 m home distance. Mild random seed 3 failed
return/time despite zero contacts/fence breaches and .732488875 m corridor
clearance; its original watchdog RTL and actual disarm remain preserved.
Mild random seed 4 passed navigation at 863.2 airborne seconds. Field 3
and mild random 4 reported DEGRADED precision, a retained quality limitation.
V22 cannot qualify and no full suite was run on it. Exact source/configuration,
original grades and connected disarm are closed in its per-artifact review.
V23 now owns ROOT and the new trials.

# Current checkpoint: V22 provisional

No accepted source. V22 freezes 926 controlled files, archive SHA256
bd6a5c76a5432a93a71eefb01b106851143c812a4e9aa58260b9b6e26d9bf529.
All 11 normal-startup imports match. 287 focused checks pass. V21's early-orbit
change was rejected after flight results and removed from this candidate.
V22 keeps all twelve initial search headings, then tries the existing bounded
guarded orbit before repeating a full sweep if that first sweep observed a
stable, whole, fresh non-outbound green lead. Green is observation geometry,
never identity or crossing permission. Empty/invalid leads retain normal search.

Gate crossing still requires pose, velocity and lidar age at most .30 s and
the same .08 m/s braking threshold and distinct-sample confirmation. A transient
capture gap commands only a hold, resets settling evidence, and allows .30 s
to recover before failing. It cannot cross or hand over on stale observations.
Normal timing/actuator behavior, camera/perception and lidar filters are unchanged.

Five two-worker exact-source targeted trials are running, mild random seed 3
and field seed 2 first. One final offline suite, all five native rendered
acceptances and 96 eligible campaign flights remain gated. Reduced scope is
120 selected, 24 negative geometry classifications and 80 weather exclusions.
No original 200-case qualification is claimed. Strong gusts and artificial
control delay remain unresolved and excluded.

## V21 rejected and interrupted batch

Field seed 1 passed navigation. Field seed 2 failed return after a .31-.37 s
recorded lidar-age interval triggered GateAdvance's immediate stale-data abort.
Mild random seed 3 failed return/time, and field seed 3 failed time. Those four
actually disarmed and their original grades remain failed where applicable.
Mild random seed 4's process was interrupted with last telemetry armed at
606.01 s; final disarm and final grade are unverified. The WSL simulator owning
processes were absent and WSL uptime reset on inspection. The partial batch is
not a completed qualification. Source/run manifests and archive are verified;
all telemetry and original stderr remain in the closed interrupted-batch review.

The landing probe using the recorded initial home reference and return pose
passed before any new landing change, achieving visual lock in 9.8 s. It is
a fixture diagnostic with regenerated random streams and no ROS delivery;
it does not reproduce the field seed 2 timeout or qualify landing.

# Current checkpoint: V21 provisional

No accepted source. V21 freezes 924 controlled files, archive SHA256
8e23f88b3e18959f524b83d6ec9abcbcf424af15757cdc55d4ea6914038327ce.
All 11 normal-startup imports match this freeze. A real search-leaf regression
failed before the fix: three distinct fresh whole-region captures still waited
through repeated full sweeps. V21 starts the existing guarded orbit from a
stable non-outbound whole green lead. It requires distinct capture-associated
poses, freshness, settled camera and consistent measured lead positions.
Green alone never supplies identity or gate-crossing permission. Existing
orbit bounds, fence/red/lidar guards, normal timing and all acceptance thresholds
remain unchanged. 124 focused search/capture/framing/handover/landing checks pass.

Five two-worker same-source navigation cases are active, with retained mild
random seed 3 and field seed 2 first. Final offline, five full native rendered
acceptances and 96 eligible campaign flights remain gated. Scope stays 120
selected, 24 negative geometry classifications and 80 weather exclusions.
No original 200-case qualification is claimed. Strong gusts and artificial
control delay remain unresolved and excluded. Earlier failures are preserved.

## V20 closed result

V20 is unaccepted. Fields 1, 2 and 3 and mild random seed 4 passed all 13
navigation checks. Mild random seed 3 exceeded 900 seconds and was safely
returned by the watchdog; its original time and unexpected-mode failures
remain failed. All five actually disarmed, with zero contacts or fence breaches.
Field 2 and mild random 4 reported degraded precision landing; their navigation
checks passed but this quality limitation is preserved. Fixture payload delivery
remains unmeasured and no motor delivery qualification is claimed.

The mild seed 3 search occupied simulated seconds 717.57 to 817.20. A whole
green region near the later orbit lead was visible in recorded snapshots by
724.13, but the orbit began after both complete sweeps. Snapshot green replay
uses the recorded pose and no lidar and is an approximate diagnostic, not a
complete 20 Hz identity history. The landing physics probe passed before any
new landing change, achieving visual lock in 8.6 seconds; it did not reproduce
the field seed 2 precision timeout. No landing metric change followed it.

Exact source, configuration, original grades, videos, telemetry and connected
disarm are closed in
`logs/reliability_reduced_scope_v20_source_20261008/targeted_failure_closed_review.json`.
The search diagnosis is
`logs/reliability_reduced_v20_targeted_20261008/my_world_random_s3/return_search_latency_diagnosis.json`.
Final offline, all five native rendered acceptances and the 96 eligible campaign
flights remain pending. Scope stays 120 selected, 24 negative geometry
classifications and 80 excluded weather cases. Strong gust and artificial delay
remain unresolved; original 200-case qualification is not claimed.

# Current checkpoint — V20 provisional

No accepted source. Frozen 923 files; archive SHA256
ecf1a1db32d94d422929b4b8bdf3979640036e8429a27980876548f150e37175.
All 11 normal-startup module imports match this freeze. V19 passed return,
QR search, clearance and time checks for all five targeted cases; fields 1/3
and mild random 4 passed navigation, while field 2 and mild random 3 failed
home landing at 1.67/2.19 m. All five actually disarmed; no contacts/fence breaches.
Those failed grades are closed and preserved, not upgraded.
The actual flown tree commanded 5 m home altitude although its own landing
leaf required 8.48 m for acquisition and 6.98 m for tracking. It immediately
committed below the tracking floor without observing the home marker.
The real built-tree regression failed; V20 wires home return to the existing
derived landing acquisition altitude. 230 focused startup/landing/routing
checks pass. Return framing, perception, normal timing, actuator response and
all acceptance thresholds are unchanged from V19.
Two-worker V20 targeted trials are active, with retained mild random 3 and
field 2 first. Final offline, all five native rendered acceptances and 96
eligible campaign flights remain pending. 24 invalid/infeasible geometry
classifications and 80 excluded weather cases are not passes; no original
200-case qualification is claimed. Strong gusts and artificial control delay
remain unresolved and excluded. All failures and recordings remain preserved.

## Prior checkpoints

# Current checkpoint — V19 provisional

No accepted source. Frozen 922 controlled files; archive SHA256
79d3aa68390c2c0fd90ab6a449f2528ae396cc23fa3d5357f1749cc56144f5cc.
Normal startup imports match the freeze for all 11 checked modules. Return
framing now consumes four distinct fresh identified horizontally clipped
captures during yaw settlement and uses the existing 2 m backoff, shared
maximum of two attempts. Accepted board range, plane, crossing permission,
camera tilt requirements and every acceptance threshold are unchanged.
The actual leaf regression failed before the fix; 92 focused return/gate,
capture and clearance checks pass. Another 98 integrated component checks pass.
V18 closed 4/5 normal-timing navigation cases: fields 1/2/3 and mild random 4
pass; mild random 3 fails return/time and was safely stopped with operator RTL.
Every case has actual connected disarm, no contacts and no fence breaches.
V18 is not accepted. Its LAND model correction retains estimated-position
control, as the installed ArduPilot source does; physical response, wind,
normal callbacks and zero added queue are unchanged.
V19 targeted trials are active. The final offline suite, all five rendered
acceptances and 96 eligible campaign flights remain pending. Prior-source passes are not
reused as V19 qualification. 120 selected entries include 24 negative geometry
classifications; 80 weather entries are excluded. The original 200-case
qualification is not claimed. Strong gusts and artificial delay remain
unresolved and excluded. All failures and recordings remain preserved.

## Prior checkpoints

# Current checkpoint — V17 provisional

No accepted source. Frozen 920 files; archive SHA256
e5317625c74e9cce0edc19c1ad567ebe4cee48cae8aea9dc32cde810d262b25d.
Only the passive winch-arrival recording changed from V16, plus nine regression
tests. Controller, perception, contact grader and all thresholds are unchanged.
The actual callback/contact-grader seam reproduced the missed capture before
the fix; 62 focused recording/contact/qualification checks pass.
Normal startup imports match this freeze. The final offline suite passed
1,544 tests, three empty real-photo corpus skips, and all syntax/config/frontend
checks. The five parallel navigation cases passed 2/5: field 1 failed return
and .70 m clearance (.671739 m), field 3 failed time, and retained random 3
failed time/home landing. All disarmed; original failures remain preserved.
Three same-source/configuration cases are being probed with two workers after
the full suite finished, to isolate concurrent-check timing. Five rendered acceptances and
96 campaign flights remain pending. V16 split failed 17/22 after 18 contacts
failed only the unchanged 0.30 s winch freshness requirement. Operator RTL,
actual connected disarm and all original grades/recordings are preserved.
24 negative geometry classifications and 80 weather exclusions are not passes.
Strong gusts and artificial delay remain unresolved and excluded.

## Prior checkpoints

# Current checkpoint — V16 provisional

No accepted source. Frozen 919 files; archive SHA256
e53a52e3566ff5a95d271cdfa8eade000ea22ff853af578561bdcd7052a6351e.
Retained mild-weather random 3 passed all 13 navigation checks: 882.3 s
airborne, .738496400 m corridor clearance and 2.171071264 m red clearance,
zero contacts/fence breaches and actual connected disarm. Normal timing and
actuators retained. Fields 1/2 passed all 13 navigation checks (751.7/797.2 s airborne,
.740502577/.737166208 m corridor clearance, actual disarm and zero
contacts/fence breaches). Field 3 and retained random 4 also passed all 13 checks. All five targeted
navigation cases are closed on V16 with matching source/configuration hashes.
The final offline suite passed: 1,535 tests and all syntax/configuration/frontend
checks; three empty real-photograph corpus tests were skipped. Native split-course
acceptance is active, with motor delivery confirmed and return in progress.
This fixture does not qualify rendered vision or motor delivery.
Return framing now consumes distinct fresh onboard-pose-associated captures
during yaw settlement as well as dwell. Existing three-capture requirement,
0.5 m same-XY raise, maximum three climbs and all identity/lidar checks remain.
Top-cropped lettering during a turn guides only bounded framing recovery.
378 focused routing/return/gate checks pass, including the new red/green real-leaf control
and stale, replay, tilted and outbound rejection. Final offline evidence is closed
with all 919 source hashes unchanged.
V15 passed 12/13 navigation checks, failing only time at 905.0 s.
Both corridor traversals, .728450848 m corridor clearance, 1.533766164 m
red clearance and connected disarm passed; the RTL request is preserved.
Original failures, source/configuration hashes and artifact hashes are closed.
Strong gusts and artificial delay remain unresolved and excluded.
Five rendered acceptances and 96 campaign flights pending;
24 negative geometry classifications and 80 weather exclusions are not passes.

An issued segment is now certified against every original observed rectangle
inflated by the unchanged 1.50 m clearance before merged routing boxes can
reject it. Actual-margin starts still require the restricted escape.
A captured V15 command reproduced the false brake before the fix.

## Prior checkpoints

# Current checkpoint — V15 provisional

No accepted source. Frozen 917 files; archive SHA256
4d44298738fe7c4d677ca337326ae95f92b8f5b92a9e86d884383c2ebd091fe6.
Retained mild-weather random 3 passed all 13 navigation checks: 882.3 s
airborne, .738496400 m corridor clearance and 2.171071264 m red clearance,
zero contacts/fence breaches and actual connected disarm. Normal timing and
actuators retained. Fields 1/2 passed all 13 navigation checks (751.7/797.2 s airborne,
.740502577/.737166208 m corridor clearance, actual disarm and zero
contacts/fence breaches). Field 3 and retained random 4 also passed all 13 checks. All five targeted
navigation cases are closed on V16 with matching source/configuration hashes.
The final offline suite and full native split-course acceptance are active.
This fixture does not qualify rendered vision or motor delivery.
Return framing now consumes distinct fresh onboard-pose-associated captures
during yaw settlement as well as dwell. Existing three-capture requirement,
0.5 m same-XY raise, maximum three climbs and all identity/lidar checks remain.
Top-cropped lettering during a turn guides only bounded framing recovery.
258 return/gate checks pass, including the new red/green real-leaf control
and stale, replay, tilted and outbound rejection. No final offline run yet.
V14 failed return/time acceptance; recorded RTL and connected disarm verified.
Original failures, source/configuration hashes and artifact hashes are closed.
Strong gusts and artificial delay remain unresolved and excluded.
Final offline, five rendered acceptances and 96 campaign flights pending;
24 negative geometry classifications and 80 weather exclusions are not passes.

## Prior checkpoints

# Current checkpoint — V14 provisional

No accepted source. Frozen 917 files; archive SHA256
d356f83014d2abb0e5ebe991810a29bebd5ad1432ad04272d895c8a5cb899d2b.
Retained mild-weather random 3 passed all 13 navigation checks: 882.3 s
airborne, .738496400 m corridor clearance and 2.171071264 m red clearance,
zero contacts/fence breaches and actual connected disarm. Normal timing and
actuators retained. Fields 1/2 passed all 13 navigation checks (751.7/797.2 s airborne,
.740502577/.737166208 m corridor clearance, actual disarm and zero
contacts/fence breaches). Field 3 and retained random 4 also passed all 13 checks. All five targeted
navigation cases are closed on V16 with matching source/configuration hashes.
The final offline suite and full native split-course acceptance are active.
This fixture does not qualify rendered vision or motor delivery.
Return alignment consumes distinct fresh banner captures paired with onboard
poses, allowing the existing bounded clipped-view recovery to trigger.
Small speed increases retain the already acknowledged lower cap; every speed
decrease still requires acknowledgement. Search/detector checks pass 154;
return/gate checks pass 252 (overlapping counts, not additive).
V13 failed return and elapsed-time acceptance, with recorded RTL and actual
disarm. Its source, configuration and artifact hashes are closed and preserved.
Strong gusts and artificial delay remain unresolved and excluded.
Final offline, five rendered acceptances and 96 campaign flights remain pending;
24 negative geometry classifications and 80 weather exclusions are not passes.

## Prior checkpoints

# Current checkpoint — V13 provisional

No accepted source. Frozen source: 916 controlled files, archive SHA256
5159a424f99dbaf793204ef3061e6dacf7b949565bd4137313ffde20c6fdbcd8.
Retained random seed 3 is active. Search braking consumes actual delivered
FCU velocity captures instead of snapshots of that stream at the slower
mission timer. The unchanged .10 m/s threshold, three distinct fresh captures,
post-brake epoch and intervening-motion resets are covered at the real callback
and leaf seams. Earlier code both missed valid settled intervals and missed
motion between leaf snapshots; both red controls are archived. 137 focused
checks pass. Return-gate .08 m/s and .3 s stability requirements are unchanged.

The object fixture camera now matches the native model's existing 20 Hz;
lidar remains 10 Hz, physics and actuator response unchanged, configured frame
drops and latency retained. This mismatch has a red real-run-loop regression
and native sensor-definition comparison. Rates are explicit per-run metadata.
V11 and V12 retained random 3 failed time and ended in recorded RTL and actual
connected disarm. Their failure grades, configurations and hashes are closed.
Final field seeds, offline suite, five rendered runs and 96 eligible campaign
flights remain pending. The 24 negative geometry classifications are not
passes, and 80 weather cases are excluded. Strong-gust/delay failures remain
unresolved, preserved and excluded from current qualification.

## Prior checkpoints

# Current checkpoint — V11 provisional

No accepted source. V11 is frozen at 914 controlled files, archive SHA256
08651f2d5ae06b5504ca195012f54c8f1c90fa07b226adcc595386db9b86b866.
Retained random seed 3 is active. Braking now captures the measured settled
position for the turn and speed-acknowledgement anchors. Speed/detector waits
freeze their hold instead of chasing every noisy pose update. Real leaf
regressions reproduced both defects and 108 relevant checks pass.
V9 and V10 field 1 passed navigation; retained random 3 failed in both,
with recorded operator RTL and actual connected disarm. Both closed reviews
preserve every grade and artifact hash. Current-source required field seeds,
final full offline, five rendered acceptances and 96 eligible campaign flights
remain pending. The 24 geometry classifications are not passes; 80 weather
cases are excluded. Strong-gust/delay failures remain unresolved/excluded.

## Prior checkpoints

# Current checkpoint — V10 provisional

No accepted final source. V10 is frozen at 914 files, archive SHA256
4ae04641a3a81a36e4e2dd5b0da00aa712e87d03a842340d2df86e411265bd45.
Field 1 and retained random 3 are active. Search/router regressions pass 66,
including stationary turns after braking. V9 field 1 passed navigation;
random 3 failed and was safely stopped through recorded RTL and actual disarm.
Strong-gust/delay failures remain unresolved/excluded. Final offline, all five
rendered acceptances and reduced campaign remain pending. See the consolidated
evidence report for the current state and exact 96/24/80 scope.

## Prior checkpoints

# Current reduced qualification

No accepted final source exists. Strong-gust and artificially delayed-control
failures remain unresolved, preserved and excluded. The original 200-case
qualification is not claimed.

V9 is provisional: 914 controlled files, archive SHA256
681ec251b87cc2f9899c2d27b6bc71345801537fbca812d56ea8b16c98204225.
Field seed 1 and retained mild-weather seed 3 are being tested at RTF2,
zero extra transport queue, normal .6 s actuator response and .20 s budget.
The braking hold handoff regression reproduced the V8 deadlock before the
fix. After the fix, 65 search/router checks pass, including the real leaf
commanding a certified escape, replacement unsafe commands braking and
stale motion evidence preventing release.

All five V8 trials failed in battery-triggered RTL. Their connected FCU
disarm and artifact hashes are closed in
logs/reliability_reduced_scope_v8_source_20261008/targeted_failed_closed_review.json.
No operator abort was performed on those already closed trials.

Earlier V3 field seeds 1/2/3 passed navigation and its offline suite passed
1477 with 3 skipped; those sources differ and cannot qualify V9. V7 retained
mild-weather seed 4 passed; seed 3 spent 799.6 s searching for the delivery QR
and failed. All failures remain preserved.

Campaign plan: 120 selected weather cases, of which 96 are eligible flights
and 24 are existing invalid/infeasible geometry classifications. Another 80
weather cases are excluded. Executed campaign flights: zero. No geometry
classification is a traversal pass. Required final offline, five rendered
acceptances and reduced campaign are pending.

## Prior checkpoints

# Current reduced qualification

No accepted final source exists. Strong-gust and artificially delayed-control
failures remain unresolved, preserved and excluded from the current scope.
No original 200-case qualification will be claimed.

Frozen V8 archive SHA256:
5d7e4d08abafdbe117aaec7f0cf7857a19e29d4232dc7dd57b2fd4dc356eb6e9
There are 914 controlled files. Normal startup now contains stationary return
framing, an initial settled level-camera sweep with the down tilt retained,
measured-arrival gate braking, active-position-intent search braking and
batched motion clearance certificates using exactly the previous sampled points.
Thin-obstacle observations, .70 m clearance, .20 s computation deadline,
physical actuator response and native startup defaults remain intact.

349 framing/gate/contact checks, 130 search/routing checks, 37 batched-motion/
planner/deadline checks, and 54 framing/contact checks pass in the focused logs.
Counts overlap and must not be added. The 104-segment equivalent benchmark
measured 6.332 ms median individual queries versus 1.159 ms batched, 5.465x.
The initial deadline test run had three errors after its injection seam moved;
those tests now inject at the batched certificate and pass without changing
any deadline, stale-pose, pending-packet or stop assertion.

V8 field seeds 1/2/3 and retained random seeds 3/4 are running with RTF2,
zero injected transport queue, .6 s physical response and .20 s budget.
V5 field 1/2 passed; field 3 lost .70 m clearance after a .36 s certificate
overran the .20 s budget at RTF4. Exact same V5 field 3 at RTF2 passes all13
navigation checks, zero contacts/fence, actual disarm, 841.7 s total simulation.
This distinguishes runtime load from an artificially delayed physical plant.
V7 retained random seed4 passes navigation and disarms in 768.5 s simulation;
seed3 remains FAIL due lengthy QR search and return battery abort.
All earlier failures remain immutable and are not reused as qualifications.

V3 passed all three field seeds and its full offline suite, 1477 passed/3 skipped,
but these are earlier-source evidence. Its rendered split remains FAIL21/22:
completed/disarmed, .717814637943243 m corridor clearance, 215 deployed-hook
contacts with delivery floor. New native recording requires contact points,
fresh winch receipt and fresh independent airframe pose to distinguish intended
target-surface deployment from aircraft/wall/stowed/stale/off-target impacts.
Old recordings lack these measurements and cannot be promoted to passes.

Current matrix audit: 200 original entries, 80 strong-weather exclusions,
120 selected; 96 eligible flights and 24 no-flight classifications: 12 invalid
editor_test entries and 12 preserved infeasible my_world_offaxis entries.
These classifications are not traversal passes. Exact audit data is in
logs/reliability_reduced_scope_v8_source_20261008/planned_geometry_scope.json.
Final targeted closure, one final full offline suite, all five same-source
rendered acceptances, the 96-flight reduced campaign and final accepted-source
report remain pending. Object navigation cannot qualify rendered perception
or motor delivery.

## Prior checkpoints





# Current progress

Latest continuation: the 903-file arrival-anchor/framing candidate passes
field seed 1, all navigation checks, 816.3 s airborne, corridor minimum
0.758250277 m, red minimum 2.298071264 m, zero independent fixture contacts,
both corridors and actual connected disarm. Source/assets/archive verified.
Seed 2 is running against the SAME archive; seed 3 remains pending.
Archive SHA256: 9431676002ac84aabb134924689a945a19eadee0837822cec2e3f1c7331c18c2.
These are object-level navigation trials, without rendered/motor qualification.

The preceding scoped/fine source passed seeds 2 and 3 (800.8/881.4 s),
but seed 1 exceeded time at 915.3 s; it cannot be adopted. The camera-focus
source then failed seed 1 gate braking and contacted the board during RTL
at 825.24 s. Its legacy geometric contact checkbox passed incorrectly;
the unchanged run.json contact record and closed review explicitly reject
contact-free qualification. Earlier grade files remain preserved.
The real gate crossing regression fails before the measured-arrival anchor
fix, then 227 gate/fail-closed/router tests pass with the fix. Independent
headless contact grading fails five controls before correction; 20 contact
and campaign controls pass afterward. All fixture contacts must be supplied;
missing or malformed evidence cannot qualify an empty contact history.

Native contact coverage is also incomplete in earlier acceptance recordings:
evaluation_contacts.jsonl covers PAYLOAD contacts only. New passive sensors
cover each directly collidable CAD vehicle link without changing collision
geometry or mass; two structural tests pass. A normal-startup unarmed native
smoke is testing actual native topics and ground-contact canary recording.
No mission qualification is claimed for this smoke. Existing 22/22 split
guard result remains an unchanged legacy grade, not proof of new body-contact
qualification. Future final rendered runs must include vehicle contact truth.

The scoped escape root offline archive passed 1443 tests, 3 skipped, and all
syntax/configuration/frontend checks. Archive SHA256:
8f01ab5ca6fe9ae2572bae62f6e38a6998aab016075dfc1b5eac6eb6f37db70f.
Root has changed since that checkpoint (arrival braking and contact evidence);
a new full offline run is required. No accepted final source exists.

The recent 1 s empirical reserve gust diagnostic is rejected: dirty0 and
late1 both time out without traversal; late1 minimum clearance is 0.500754 m.
The dirty-calm regression also stalls (0.822993 m minimum). Original failed
launch guard logs are retained separately. No wider lidar filter, reduced
clearance, empirical recent-reserve policy or faster delay is installed.
Strong coupled gusts remain unresolved. All five final rendered acceptance
cases, corrected 200-case campaign and accepted-source report remain pending.

## Earlier checkpoints (superseded as current status)



Latest closed tests: monotonic escape source passes 1442 tests, 3 skipped,
and all offline checks, verified against its unchanged 900-file archive.
Field seed2 finds the target at 601.70 simulated seconds (previous source
707.15) but fails return alignment and lands/disarms at 998.5 s airborne.
It has no obstacle contacts/fence breaches. Its 1.169191 m corridor minimum
does not qualify return traversal, which was not completed. Source/assets
and actual FCU disarm are verified; rendered cameras and motor delivery are
explicitly unqualified for this object-level trial.

Recorded-pose return projection corrected to the runtime 0.851919 rad HFOV:
all ten early alignment captures give zero geometrically admissible headings
on the 45-degree sweep, while the 15-degree sweep supplies admissible views.
The level camera misses the board vertically; a 20-degree look sees it.
The original 60-degree replay is retained as invalid runtime configuration,
not a qualification result. Geometry is only a detection precondition.
An isolated fine-framing candidate adds one bounded finer sweep, restoring
the look angle only above gate height, before physical relocation. It retains
the original lettering, freshness, range and lidar checks. Four component
controls pass. Its 901-file archive SHA256 is
dec801079383efa322d64caecc60da2850ead40253b8a40cb72725c27ae641df.
Field seed2 is active under logs/reliability_fine_return_framing_field_s2_navigation_20261007.
An initial launcher registration path error occurred after the valid freeze;
the existing archive was preserved and registration completed separately.

Derivative-cap-only gust diagnostic: dirty0 contacts at 6.1 s, late1 at 19.0 s;
logged preintegration minima 0.402512/0.408085 m. The exact baseline/candidate
and runner are archived in logs/reliability_derivative_cap_1_6_coupled_20261007.
Baseline class methods match current root; its startup wrapper differs.
Candidate rejected. No wider lidar filter or clearance reduction is installed.
No accepted final source or 200-case qualification exists.


07 October continuation: the isolated guard's full rendered split mission
closed GRADE_PASS, all 22 required checks passed. Native minimum corridor
clearance is 0.7380697531 m, restricted-zone clearance 3.2156264652 m,
flight time 455.0 simulated seconds, payload error 0.10 m and home landing
offset 0.31 m. Recorded FCU disarm, calibrated motor delivery, camera timeline,
runtime/source/archive hashes and owned module imports are verified in
logs/reliability_render_split_guard_full_s20261003_20261007/closed_full_review_20261007.json.
Search QR/red captures each measured 20.0 Hz in simulated time, about 5.16 Hz
on the host; p95 simulated processing latency is 0.233/0.231 s respectively.
This closes the previously active split run. The guard remains isolated:
coupled gust cases fail and other required courses/final source are pending.

The field-2 timing audit now separates return BANNER_ALIGN (142.38 s) from
outbound alignment, and records SEARCH_QR 595.53 s, 250.13 m of captured FCU
travel. Repeated braking/replanning is present even with unchanged exclusion
counts. A minimal regression proves 2 cm cross-track motion invalidates the
exact nearest-edge escape endpoint. The root router now allows continuation
through that same nearest exit edge only if distance to every observed paint
rectangle is nondecreasing; existing paint and other-obstacle checks remain.
The reproduction first fails (1 failed, 12 passed); related tests then pass
127/127 including rejection of a diagonal that initially approaches paint.
This correction is provisional. Frozen 900-file source archive SHA256 is
23eb0534d929bf23920bc7aafe96647ca1fee2a01c116458dd16211d3c55a5d9.
A field-seed-2 object-level trial and a full offline rerun are active under
logs/reliability_monotonic_search_escape_*_20261007. No new flight result is
claimed. The prior 1440/3 suite belongs to the earlier source. The 200-case
campaign and accepted-source designation remain pending.

Historical checkpoints below are retained; the continuation above supersedes active-run claims.

Verified 07 October 2026, 19:26 India. Provisional integration is under test;
there is no accepted final source yet. Prior failures remain qualification failures.

- Split return failure attributed postflight: drift continues after all motion
  certificates are rejected. Original native minimum remains 0.6869707 m.
  The integrated stationary-entry repeat closed FAILED with 0.678049 m minimum;
  recovery exhausted at the next bottleneck. The trace-equipped repeat also
  closes FAILED at 0.685551 m, with camera/disarm evidence and 8 MB of
  certificate forecasts archived. The target-echo diagnostic closed FAILED
  at 0.691816 m with actual disarm. Echo lag upper observations (421 matches)
  are median 0.048 s and p95 0.057 s, not a qualified receipt bound. A causal
  no-wind fixture proves exact-delay mismatch admits unsafe motion. The added
  no-helpful-disturbance guard repairs that fixture but fails both coupled
  gust cases. The frozen native guard diagnostic passes 7/7 focused checks
  at 0.702154 m minimum, with traversal, native disarm, camera timeline,
  six-node audit and frozen source/import verification. It remains isolated
  because the coupled gust cases contact. It used the archived FCU entry pose, unchanged CAD vehicle/course and 0.70 m
  clearance plus 0.025 m planning reserve. Full mission qualification is separate.
  A full rendered split mission on the frozen guard source is active, with
  outbound traversal complete and delivery search in progress; the host-table elapsed column is
  distinct from recorded airborne time. FCU review shows only about 210 s
  armed during winch deployment; there is no established time failure.
- Field-2 router deadlock reproduced using two overlapping observed exclusion
  cells. Sequential nearest-edge escape and preserved escape waypoint repair
  pass 114 route/search checks. The frozen physical repeat now finds the target,
  completes both corridors and disarms: 0.7301542 m corridor, 1.5108600 m
  exclusion clearance, zero contacts/fence breaches. It FAILS 900 s with 942.8 s
  airborne. The repair is installed; final source qualification remains pending.
  Current integrated repeat finds the target but still fails time (951.7 s),
  at 0.753871 m corridor / 2.267071 m red clearance with no contacts. A new
  braking/router escape conflict is repaired and passes 125 tests. That
  frozen repeat fails time at 1028.9 s with clearances preserved, then
  battery-critical landing/disarm. Oblique area-range handoff again loses
  the board; the observer-viewpoint candidate also fails after
  lowering/range rejection loses the board; it is rejected, not installed. Object-level frames/receipt omissions are explicit.
- Rotated rendered seed 20261003 closed 18/22 FAILED. Once its flight budget
  was irrecoverably exceeded, the normal abort guard was requested and actual
  RTL landing/disarm recorded. Airborne 1070.1 s; return traversal, unexpected
  mode, time and 1.50 m red clearance fail (minimum 1.48 m). Motor delivery
  confirms only after complete hook retraction. Original camera and telemetry
  records remain archived with the operator intervention explicitly recorded.
- Capture inbox, buffered scan/pose pairing, independent ROS clock, computation
  deadlines and optional forecast recorder are provisionally integrated into
  the normal avoidance entry point. Gate crossing now requires acknowledged
  speed admission, fresh FCU motion/lidar, distinct settling samples and an
  acknowledged navigation-speed restore in the normal tree.
- Native avoidance/mission build passes. Production gate fault checks: 12 pass.
  Current focused controller/router checks: 89 pass. Startup/gate/mission checks:
  204 pass. First complete offline run: 9 failed, 1402 passed, 3 skipped;
  syntax/configuration/frontend pass. Corrected instantaneous fixtures pass
  all 52 affected checks. Corrected full suite passes 1427 tests, 3 skipped,
  plus syntax, configuration and frontend; production .20 s budget and
  separate deadline tests retained. Original failures preserved. Latest search-braking/campaign changes pass
  125 related and 14 gate tests; the root full offline rerun passes 1440 tests / 3 skipped,
  syntax/configuration/frontend, matched to the pre-run 900-file freeze.
- Separate actuator/disturbance forecast correction still contacts obstacles
  in dirty seed 0 and late seed 1 with physical 0.4 s delay and 0.6 s response.
  It is rejected and not installed. Wider lidar filtering remains rejected.
- Next required qualification: resolve split recovery and field-2 time failure,
  strong gust/delay; then final-source offline checks and all 22 checks on
  standard 20261003/1001, shipped, rotated and split courses. The corrected
  200-case campaign remains gated. No historical or focused pass substitutes
  for these requirements. Accepted source/configurations/detector-rate report
  cannot be finalized until those runs pass.

## Historical status snapshots

Verified 07 October 2026, 14:55 India. This section supersedes historical snapshots below.

- Complete offline checks pass on the current 839-file production source:
  1404 tests passed, 3 skipped; syntax, configuration and frontend pass.
- Fresh split seed 20261003 closes 17/22 FAILED, after landing and disarm.
  Return alignment now succeeds and the corridor is attempted, but recovery
  exhausts. Corridor clearance is 0.686971 m, below 0.70 m. Return traversal,
  corridor altitude, unexpected mode and zone ceiling also fail. Exclusion
  clearance passes at 3.186835 m. Motor delivery qualifies after full hook
  retraction on attempt one; independent payload error 0.10 m. Flight 456.1 s,
  home error 0.12 m. Full videos, source archive and runtime assets verified.
- Search detector capture rates on that recording are QR 18.0608 Hz and
  red 17.9786 Hz in simulated time; host delivered rates 4.6854 and 4.6640 Hz.
  Both p95 capture-to-processing latencies are about 0.24 simulated seconds.
  Whole-recording camera and search rates have different sampling windows.
- Rotated seed 20261003 is running on the same frozen production source.
  It has found the target and reached centring. Final result remains pending.
- The original isolated deadline controller closes seven passes and three
  failures across ten calm/field navigation runs. It was not adopted.
- A separate capture inbox reduces actual ROS scheduling-probe median pose
  age from 92 to 10 ms. Its frozen 760-file physical repeats pass field 1
  with 0.747428 m clearance, 884.1 s airborne, and field 3 with 0.734799 m,
  845.9 s. Both complete both corridors and disarm. Field 1 has no stale
  observation faults across 530 recorded decisions. These are navigation
  only; no rendered perception or delivery qualification is inherited.
- New inbox field 2 fails QR search, with 0.760675 m clearance and 542.3 s
  airborne. Its source, assets and failed recording through disarm are
  verified too. Remaining-seven expansion is withheld. The first closure
  watcher started before report creation and exited; the direct retry verifies
  both completed results. No physical result was discarded or changed.
- Normal gate-braking integration and final controller adoption remain pending.
  A staged optional-recorder startup fix passes two startup/cleanup checks.
  Strong gust/delay failures remain unresolved. A wider lidar filter was
  rejected for losing thin obstacles and retaining coupled contact failures.
- Still open: return recovery and clearance, field-2 search, strong gust/delay,
  final-source standard 20261003/1001 and shipped/rotated/split acceptance,
  corrected 200-case campaign and final report. Older passes remain historical.
- Requirements remain 0.70 m corridor plus 0.025 m planning reserve, 1.50 m
  exclusions, 900 s airborne and all 22 rendered checks. Off-axis fixture/hash
  are preserved. Motor priority and three-attempt full-hook-retract-and-continue
  remain intact. Hardware qualification and staged flights remain deferred.

## Historical status snapshots

# Current progress

Current state as of 07 October 2026, 14:03 India. This section supersedes historical descriptions below.

- The latest complete offline suite PASSES: 1404 tests passed, 3 skipped,
  plus syntax, configuration and frontend checks. Frozen source is unchanged,
  839 files, archive verified. Five installed decision modules resolve to
  those exact frozen source files. The two earlier fixture failures were
  fixed by adding clock and motion captures to teleport tests, with all
  original assertions and production freshness checks retained.
- The fresh rendered split seed 20261003 trial passed readiness, took off
  and is searching for the target QR. It is recording through disarm under
  logs/reliability_render_split_corridors_s20261003_early_red_clipped_bearing_fixture_clock_20261007.
  Rotated acceptance follows automatically. No rendered outcome is available
  yet. Seven installed perception/search repairs have full offline coverage.
- The deadline controller closes seven navigation passes and three failures
  across all ten calm/field seeds. Every calm seed and field seeds 4/5 pass
  with the 0.725 m planning reserve. Field 1 fails at 0.625300 m clearance;
  field 2 exceeds time at 981.0 s; field 3 fails at 0.681424 m clearance.
  Exact source, assets, commands, forecasts and independent truth through
  actual disarm are verified for all ten. Production adoption is withheld.
- An actual ROS scheduling diagnostic reproduces old capture delivery during
  a slow control callback: median pose age 92 ms. A separate capture inbox
  reduces it to 10 ms and applies observations only between control ticks.
  An isolated 760-file candidate is repeating failed field seed 1 with
  unchanged geometry, physics and clearance under
  logs/reliability_capture_inbox_field1_navigation_20261007. No result yet.
- A staged normal-startup repair makes diagnostic recording optional and
  passes two startup/cleanup checks after reproducing the original KeyError.
  Normal gate integration remains pending. No root controller was changed
  during the ongoing frozen perception qualification.
- The wider lidar median filter is rejected: both coupled gust/delay cases
  still contact, and it loses thin obstacles in seven of 36 controlled cases.
  Strong gust/delay qualification remains open. Failed baseline, steering
  margin and certificate-batching alternatives are retained as failures.
- Final-code standard seeds 20261003/1001, shipped/rotated/split rendered
  acceptance with motor confirmation and measured detector rates, the
  corrected 200-case matrix and final evidence report remain unfinished.
  Older standard/shipped passes do not qualify these changed decision files.
- Corridor clearance stays 0.70 m plus 0.025 m planning reserve, exclusions
  1.50 m, airborne limit 900 s, and rendered acceptance 22 checks. Off-axis
  world/hash stay preserved. Motor priority and three-attempt full hook
  retract-and-continue remain unchanged. Hardware and flights remain deferred.

## Historical status snapshots

# Current progress

Current state as of 07 October 2026, 13:24 India. This section supersedes historical descriptions below.

- The complete 839-file offline run closed with 1402 passed, 2 failed,
  3 skipped. Syntax, configuration and frontend checks passed. Both failed
  search fixtures omitted timestamped motion captures, which correctly kept
  the new braking gate stopped. Correcting only those teleport-fixture inputs
  passes their unchanged assertions and all 184 related checks.
- The complete suite is now rerunning on newly frozen source under
  logs/reliability_early_red_clipped_bearing_fixture_clock_qualification_20261007.
  Split and rotated rendered recordings start only after it passes. The first
  launcher reused an existing output path and ran no tests; retry 1 is active.
- The isolated deadline controller completed all three focused physical
  navigation trials. Field 4: 793.6 s, 0.753576 m corridor, 2.185071 m exclusion.
  Field 5: 811.3 s, 0.726896 m corridor, 2.224071 m exclusion. Calm 5: 867.7 s,
  0.745085 m corridor, 2.202071 m exclusion. Both corridors were traversed,
  all 13 navigation checks passed, no contacts, actual final disarm. Frozen
  source, assets and complete evidence hashes are verified. These headless
  runs do not qualify rendered perception or delivery.
- The seven remaining calm/field seeds are running with the same frozen
  candidate, physical 0.4 s delay, 0.6 s response and 0.20 s computation budget
  under logs/reliability_command_deadline_extended_navigation_20261007.
  The production controller remains unchanged during perception qualification.
- Seven perception/search files are installed. Pristine analysis pixels,
  clipped-banner bearing before area-derived range, provisional camera red
  boundaries and braking before replanning are covered by focused tests.
  Fresh rendered acceptance on these changes is still pending.
- The last pristine split recording closed 19/22 FAILED, with motor delivery
  qualified, payload error 0.11 m, 773.1 s airborne and final disarm. Return
  traversal, unexpected mode and zone ceiling failed. Its complete video,
  source and runtime assets remain archived. Older standard/shipped passes
  are historical evidence and do not qualify the current source.
- Strong changing gusts with command delay remain unqualified. The deadline
  candidate still fails the two preserved dirty/late narrow-corridor cases.
  Extra steering reserve and two batched certificate optimizations were
  rejected. No clearance, physics or acceptance assertion was relaxed.
- Final-code standard seeds 20261003/1001, shipped/rotated/split rendered
  acceptance, the corrected 200-case matrix and the final report remain open.
  Source hashes, onboard commands/telemetry and separate truth are retained.
- Requirements stay 0.70 m corridor clearance plus 0.025 m planning reserve,
  1.50 m exclusion clearance, 900 s airborne and 22 rendered acceptance checks.
  Off-axis geometry/hash stay preserved. Delivery remains motor priority with
  three attempts, full hook retraction, then continue unconfirmed. Hardware
  qualification and staged flights remain deferred.

## Historical status snapshots

# Current progress

Current state as of 07 October 2026, 13:02 India. This section supersedes historical job descriptions below.

- The pristine-camera complete suite passed 1388 tests, 3 skipped, and all
  other offline checks. The latest production source subsequently received
  seven reviewed perception/search files; its fresh full suite is running.
- The pristine rendered split trial closed FAILED, 19/22. Motor-priority
  delivery qualified, payload error 0.11 m, flight 773.1 s, home error 0.09 m
  and actual final disarm. Return traversal, unexpected mode and zone ceiling
  failed. Exact source, video through disarm and runtime assets are archived.
- Installed repairs retain pristine image pixels, treat clipped banner
  identity as a bearing before range, expose provisional camera red edges,
  and brake unsafe search segments before replanning from measured position.
  Selected checks pass 139 banner, 130 search/routing and 94 perception tests.
  The real callback rejects all 432 labelled red-QR fixtures. Full rendered
  acceptance remains pending. No simulator truth is supplied to decisions.
- Qualification is running under
  logs/reliability_early_red_clipped_bearing_qualification_20261007. It freezes
  839 source files, runs the full suite, then records split and rotated courses.
  Standard seeds 20261003/1001 and shipped need final-source repeats afterward.
- The isolated lidar-fault observer repair passed 5 new and 29 existing checks,
  but its three physical trials are only two navigation passes and one failure.
  Field 4 completed at 791.9 s, clearance 0.716679 m; calm 5 at 872.3 s,
  0.723122 m. Both lose the 0.725 m planning reserve. Field 5 fails recovery,
  913.8 s, 0.664405 m. All source/assets/evidence verified through disarm.
  The production controller is unchanged; this is not full qualification.
- An additional 0.05 m steering-reserve candidate failed 3 of 29 existing
  checks and both preserved strong gust/delay cases. Rejected, source archived.
- Recorded certificate-to-publication delay reaches 0.18 s. An isolated
  computation-deadline candidate passes 4 new checks and 29 physical fixture
  checks with their actual zero-computation clock. Live independent-clock
  field 4/5 and calm 5 trials retain a 0.20 s budget and are running under
  logs/reliability_command_deadline_navigation_20261007. Physical delay remains
  0.4 s and response 0.6 s. Strong gust/delay qualification remains open.
- The corrected 200-case campaign remains pending targeted qualification.
  Prior failed baseline campaigns are preserved, not promoted to passes.
- Corridor clearance stays 0.70 m plus 0.025 m planning reserve, exclusion
  clearance 1.50 m, flight ceiling 900 s. Off-axis geometry/hash stay preserved
  as infeasibility regression. Motor priority and three-attempt full hook
  retract-and-continue policy remain unchanged. Hardware/flights are deferred.

## Historical status snapshots

# Current progress

Current state as of 7 October 2026, 11:30 India. This section supersedes the
historical running-job descriptions below.

- Standard rendered seeds 20261003 and 1001 previously passed all 22 checks,
  through disarm, on the archived handover-guard source. The new banner
  capture/continuity source has not yet repeated that pair.
- Previous rendered shipped passed all 22 checks. Rotated closed 20/22,
  failing 1.50 m exclusion clearance and 900 s time. Split closed 19/22,
  failing return traversal, unexpected mode and zone ceiling. All recordings
  and source archives are preserved; none of these failed courses is a pass.
- The previous complete suite passed 1376 tests. The later timestamped-banner
  suite closed with 1381 passed, 3 failed and 3 skipped. Two unstamped fixture
  failures are corrected. The corruption failure exposed a clipped-color
  detection gap previously hidden by retained OCR. Current repairs pass 209
  targeted checks. The fresh complete suite passes with 1387 passed, 3 skipped
  and all build/configuration checks passing. All 835 source hashes match.
  A fresh split rendered run is active, through delivery and onward mission
  execution. Its final grade is pending. The simulator-only contact detach
  event is recorded separately; it does not establish drone confirmation.
- The independent-clock candidate's expanded batch closed ten actual flights,
  four navigation passes and six failures. Six earlier unsupported-domain
  setup errors remain separately recorded and were retried. Controller
  adoption and changing-gust qualification remain withheld.
- The isolated scan-pose interpolation candidate passes calm my_world seed 5:
  all 13 navigation checks, 0.7407902342 m corridor clearance, 2.2050712636 m
  exclusion clearance, 883.9 s flight and no contacts, through disarm.
  Source archive 758 files is verified. Delivery was omitted and unconfirmed.
  The ten-case calm/field seed 1-5 batch is closed under
  logs/reliability_focused_paired_scan_navigation_verified_20261007. The snapshot
  is frozen. The first batch omitted the required recorder path and crashed
  the controller; it is stopped and marked invalid, with scoped cleanup recorded.
  The corrected batch closes seeds 1 and 2 with all 13 navigation checks,
  clearances 0.7358605386 / 0.7420698642 m and flight times 880.1 / 881.9 s,
  no contacts and disarm. All ten configurations have closed: six navigation
  passes and four failures. Calm
  seed 3 exhausts return recovery after losing the 0.725 m sampling reserve,
  although its minimum 0.7222927131 m exceeds the hard 0.70 m limit. Field
  seed 2 finishes and disarms but fails clearance at 0.6895136986 m. Field
  seed 5 stops at GateAdvance because fresh pose, velocity and lidar captures
  are unavailable. Field seed 4 completes and disarms at 927.7 s airborne,
  exceeding the unchanged 900 s limit. None of these failures is excluded
  from qualification. The closed batch review hashes onboard data, commands,
  lidar and separate truth, verifies the source archive and confirms disarm
  for all ten trials. Calm seed 5 passes the 0.70 m grader at 0.7234276155 m
  but loses the additional 0.025 m sampling reserve; that is not full reserve
  qualification and must be resolved before adoption.
- A separate buffered scan-pose candidate retains the last paired scan only
  while fresh and promotes a pending capture when a later onboard pose brackets
  it. Seven real-subscription callback contract checks pass. Its first broader
  controller regression closes with 23 passed and six failures using unstamped
  fixtures. Exact rejected source and failure output are archived and verified
  under logs/reliability_buffered_stamped_fixture_preparation_20261007.
  Measurement-stamped isolated fixture copies pass all 29 regressions in
  237.26 s with the same physical motion models and assertions. The two
  preserved coupled gust/delay failures still contact obstacles at 6.1 / 19.0 s.
  Full calm seed 3 now passes all 13 navigation checks at 0.7254285863 m
  corridor clearance, 2.2520712636 m exclusion clearance and 803.4 s airborne,
  through disarm. Exact 759-file source, assets, recordings and commands are
  verified in logs/reliability_buffered_scan_navigation_seed3_20261007.
  No capture-time pose faults occur in its 605 controller records; four other
  freshness stops remain recorded. This single pass does not establish general
  reliability. Field seed 2 closes with return-banner alignment exhaustion,
  954.1 s airborne and no return traversal. Its 1.0703 m sampled clearance
  cannot qualify the original return-clearance failure. All source, commands,
  observations and separate truth are verified through disarm. Production
  remains frozen.
- A separate gate-only candidate pauses for at most one second on unavailable
  observations, holds the last fresh measured position and resets distinct
  settling samples. Persistent loss, service rejection and the original
  overall timeout still fail. Five new contract checks pass for the exact
  implementation, with the original 12 interface checks unchanged. Field seed 5
  completes both corridors at 0.7333189262 m clearance and disarms, but fails
  the 900 s time requirement at 917.2 s. It has 247 capture-pose faults among
  993 controller records. Exact source and closed evidence are verified under
  logs/reliability_gate_pause_navigation_seed5_20261007.
  This candidate excludes the scan buffer, so its effect can be assessed
  separately. Its source archive is verified; no production adoption yet.
- A new combined observation snapshot contains only the checked scan buffer
  and bounded gate pause. Source archive 759 files is verified with SHA
  6047376904c047d97bdb9cefdf357dd16fb901750000740c494e012a569e2f2a.
  Its 29 controller regressions and five gate checks pass. Field seeds 4 and 5
  close with return navigator STUCK, clearance 0.6401312614 / 0.6778281715 m,
  airborne time 916.8 / 934.4 s, and disarm. These are clearance and recovery
  failures, not just alignment failures. Calm seed 5 is still active. Production
  and the active renderer are untouched; this combined candidate is not adopted.
  Combined changing-gust/delay failures remain unqualified.
- A separate actual-OCR contract proves that the current banner detector
  feeds annotation-modified pixels into OCR. The saved rendered fixture has
  8,835 changed color channels in the OCR crop. An isolated display-overlay
  separation makes the OCR input identical to normalized camera pixels.
  All 279 selected banner/camera/corruption regressions pass in 218.59 s.
  The newly prepared pixel-input regression and capture contracts pass 11/11.
  A first launcher
  used a nonexistent test filename and ran no tests; that setup error is
  preserved, and the corrected runner uses test_perception_corruption.py.
  A reviewable two-file patch adds separate display pixels and that regression.
  The owned integration job is waiting for the current native recording,
  source archive and final source guard to close. It requires actual disarm
  and the exact original 835-file manifest before changing either file. It
  will then archive the new source, run the complete offline suite and repeat
  the native split trial. Existing failures remain preserved. This repair is
  not yet installed in the frozen production source.
- Coupled changing-gust/delayed-control cases still fail with physical contacts.
  The corrected 200-case campaign is outstanding. The archived older baseline
  closed 160 flights with no navigation passes and classified 40 without flight.
- Hardware qualification and staged flights remain deferred. Motor-priority
  delivery and three-attempt full-retract-and-continue policy remain in place.

## Historical progress, retained for traceability
The expanded navigation results now qualify only 3 of 5 calm seeds: seeds 1,
2 and 4 pass with clearances 0.7288209751, 0.7307921731 and 0.7230303401 m.
Seeds 3 and 5 fail at 0.6893745645 and 0.6788924955 m and exhaust return
recovery, with no physical contacts. The original expanded launcher closes
10 records: 4 actual calm flights and 6 unsupported-domain setup failures.
Those six are not flight results. Its source remains unchanged. The separate
valid-domain retry closes calm seed 5 and field seed 1, with field seeds 2-5
still active. Field seed 1 completes return traversal but fails clearance
(0.5941080050 m) and flight time (915.1 s).

Independent diagnostics locate both new calm clearance losses at obstacle 4
inside RETURN_CORRIDOR. Seed 3 first crosses 0.70 m at 863.4 s; seed 5 at
772.7 s. These diagnostics are evaluation only, not flight inputs. A separate
snapshot is being prepared to record the original motion certificate's full
predicted paths, input timestamps and actual publication timing, with no changed
decisions or physics. Production adoption remains withheld.

The scratch settling/identification experiment also fails both preserved coupled
cases, contacting at 24.05 s and 7.25 s. Rejected code and traces remain in
logs/reliability_observed_corridor_bootstrap_20261007. It is not a qualified fix.
The rendered split-corridor trial remains active in banner alignment; its full
recording and final independent grade remain outstanding.

Full isolated clock-candidate calm seed 1 closes with all 13 navigation checks
passing: 0.7073142080 m corridor clearance, 2.0950712636 m red clearance, 839.0 s
flight, no contacts and actual final disarm. Its 756-source archive readback
verifies SHA256 a32479058127f2d7f8711125753090b26398ae5b33ecc978759879775d46cc28.
Delivery is explicitly omitted and unconfirmed; the full delivery grade remains
FAIL. This is a navigation pass only, with no production adoption.

The expanded frozen-candidate run has closed calm seeds 1 and 2 with both
navigation checks passing. Calm seeds 3 and 4 are active. A domain-allocation
mistake assigned the later six configurations unsupported ROS domains; their
setup results must not count as flight qualification. A separate bounded-domain
retry for calm seed 5 and field seeds 1-5 is running under
logs/reliability_focused_clock_navigation_domain_retry_owned_20261007. All use
the exact same frozen candidate, unchanged physical delay and response, and
navigation-only scope. Results and source comparisons are recorded per trial.

The valid-domain replay of the two preserved coupled failures still FAILS:
dirty seed 0 contacts at 6.1 s (logged preintegration minimum 0.4025115169 m),
and late seed 1 contacts at 19.0 s (0.4030209126 m). Faster planning and actual
clock delivery repair the calm full-course timing defect but do not qualify
changing gusts with delayed control. Full traces are separately preserved in
logs/reliability_clock_candidate_coupled_valid_domain_20261007. Hardware remains
deferred. The complete corrected 200-case campaign is still outstanding.

The corrected independent-clock controller now passes all 29 existing physical
loop, command-delay and FCU-velocity regressions. Its new full calm seed 1
navigation trial is running in a verified isolated snapshot, with unchanged
physical motion and command delay. Owned status is
logs/reliability_live_clock_navigation_candidate_fixed_owned_20261007/status.json.

Additional camera-only calibration detects a cropped restricted board 0.30 s
earlier using the actual frozen runtime intrinsics; 432 controlled red-ink QR
image fixtures produce no false candidates. These are not flight evidence.
The scratch return-vantage ordering preserves every observation and heading,
reducing geometric travel by approximately two thirds on the rotated example.
Both components still need clearance-aware execution and native flight validation.

Direct continuation on 7 October: the compiled planner passes 13 geometric
regressions and reduces median planning time on 39 recorded scans from 0.173 s
to 0.051 s. Its full calm navigation trial still FAILS: return minimum clearance
is 0.4865810224 m, recovery is exhausted, and RTL fails corridor-altitude and
mode checks. There are no simulator contacts. Its 755-source archive verifies
under logs/reliability_fast_planner_navigation_candidate_20261007. Actual world
callback evidence measures header-to-callback delay up to 0.400 s before the
separate configured 0.400 s physical command delay. Faster planning alone is
not a qualified fix.

An actual ROS clock integration reproduces the hidden age: a blocked 0.300 s
callback reports zero elapsed simulator time with the default executor, while
an independent clock subscriber reports 1.120 s at the same accelerated clock.
This uses only ROS time, with no simulator geometry or delivery status. The
first isolated flight prototype stopped on a forecast initialization exception;
its exact 756-source archive is preserved. After that correction, regressions
found four failures caused by accidentally removing the existing pose-derived
velocity fallback. Those rejected bytes and logs are preserved separately.
The corrected scratch candidate retains the fallback and still rejects stale
or invalid observed EKF velocity. Existing controller regressions are running
again before any next full flight. Production decision source remains frozen.

The rendered split-corridor run has passed delivery and is searching for the
return banner. It has no final grade yet. The rotated rendering remains a
20/22 failure; passing detector rates do not qualify its usable observation
distance or its 900 s mission budget.

## Standard seeds passed; broader baseline failed; corrected validation active

The nine new headless observation/receipt/terminal regressions and their related
checks pass 25 of 25. All eight owned runtime-capture path checks pass. The full
latest-source suite passes 1376 tests with 3 skips and all syntax, configuration
and frontend checks. Separate full rendered shipped, rotated and split-corridor
courses follow automatically. The fresh shipped launch passes actual absolute-
output runtime capture with 32 parameter files and 53 hashed runtime assets.
Current coordination and source
freeze are recorded in logs/reliability_observation_and_capture_qualification_20261007.

The fresh shipped rendered seed 20261003 now passes all 22 checks, with 668.0 s
flight, 0.7988818316 m corridor clearance and 1.5758952454 m restricted-zone
clearance. Motor-priority delivery and the complete camera through disarm pass.
The source/runtime archive verifies. The full rotated run closed with 20 of 22
checks passing: 1149.9 s exceeds the 900 s limit, and restricted-zone clearance
falls to 1.1590944096 m. Corridor clearance passes at 0.8402189031 m; delivery,
landing, motor evidence and complete camera through disarm pass. Its exact archive
verifies. Split-corridor acceptance has now started. See VERIFICATION.md for rates.

Work continues directly without further agents. A new acknowledged early gate
speed component passes at 0.35 and 0.50 m/s; arrival-only gating still fails.
Speed restoration, real capture freshness and full mission qualification remain
required before any candidate adoption. Coupled changing-gust repair is still
open. Rejected scratch candidates and finite safe holds are not traversal passes.

Direct continuation: the candidate now uses the actual FCU `speed` observation
key, acknowledges restoring the previous commanded speed and holds the latest
fresh measured position when another sensor becomes stale. All 10 command/freshness
fault checks pass, including rejected/missing/late acknowledgements, stale pose
and lidar, repeated velocity captures, restoration rejection and bounded settling.
The unchanged physical gate component still passes at 0.50 m/s: minimum clearance
0.8294466941 m, measured handover speed 0.0754433 m/s. This is component evidence;
an isolated full navigation candidate is being prepared without changing the
decision source of the active rendered runs.

Full candidate result: the scoped first attempt correctly refused a missing
previous navigation-speed command. With explicit restore configuration, all
12 fault checks pass and the full calm seed 1 run completes outbound traversal,
search and unqualified delivery omission, but FAILS return navigation with a wall
contact. Handover ground speed improves to approximately 0.055 m/s; return motion
then violates clearance at 770.7 s, minimum 0.4044297556 m. Its 754-source archive
verifies. This candidate is not adopted. The recorded raw commands show roughly
0.4â€“0.57 s between header capture and independent callback receipt during heavy
planning; actual world callback delay still requires separate instrumentation.
A compiled graph-search candidate is being checked against captured onboard
scans and existing geometric regressions while production decision code remains
frozen. The rotated delay separately isolates 618.205 s in return-gate search;
a scratch sighting test retains the measured zone-side camera vantage for lidar
alignment when the area-derived stand-off is outside the zone, while preserving
outside-vantage, clipped-board and outbound-board rejection. No new flight pass
is claimed from either component.

The corrected headless calm my_world seed 1 trial closed FAILED. Outbound
traversal, red-zone clearance, landing and actual final disarm pass, but return
recovery becomes STUCK at x=15.54. Minimum independent corridor clearance is
0.5028028772 m; subsequent RTL violates the corridor altitude and mode checks.
There are no simulator contacts. This is a navigation failure, not rendered
perception or motor-delivery qualification. The 833-file source archive was
independently read back and hashed. Evidence:
logs/reliability_corrected_headless_focus_20261007/my_world_calm_s1/navigation_grade.json
and logs/reliability_corrected_headless_focus_20261007/source_archive_review.json.

The earlier scratch control experiments have closed without a qualified new
traversal. Decision-producing source remains frozen at the passing standard pair
while the new rendered recordings are active.

Update on 7 October: the broader archived-source baseline closed with 200
requested combinations, 160 executed trials and zero navigation passes. The
40 non-flight combinations are 20 invalid editor_test cases and 20 preserved
off-axis cases blocked geometrically at 0.70 m. There were 38 flights with
simulator contacts, 31 recorded clearance-check failures and 22 restricted-zone
clearance-check failures. All 160 fail return traversal. Complete original
results remain in logs/reliability_navigation_baseline_matrix_assets_20261006;
aggregate_review_20261007.json gives every world and failure-check count.

Headless review found wind-induced physical ground motion omitted from FCU
velocity observations, premature clearing of the prior position target before
delayed velocity receipt, and final disarm samples omitted on some failures.
These limitations remain explicit and do not turn failed flights into passes.
The snapshot is preserved; corrections and new trials use separate evidence.

The additional shipped, rotated and split rendered launches all stopped before
mission start. capture_runtime_configuration.py only recognized relative logs/
output paths, but the coordinator passed absolute paths. The actual selector
reproduces this failure. The repaired selector matches the positional output
argument in the owned Bash process's cwd; all 8 positive/negative scope cases
pass. Fresh rendered trials are still required. Earlier setup outputs remain
in logs/reliability_baseline_rendered_courses_20261006.

The coupled-condition control repair remains open. Permanent measured-position
rejection is safe for dirty seed 0 over 150 s but fails late seed 1 at 14.1 s;
neither completes traversal. No controller change has been adopted from these
experiments. Preserve motor-priority delivery and three-attempt retract/continue.

## Previously qualified standard pair

The current-source full standard calm seed 20261003 closed successfully with
22 of 22 independent checks passing. Flight time is 865.0 s against the
900-second limit. Measured minimum corridor clearance is 0.7258271521 m;
restricted-zone clearance is 1.5967184497 m. Payload error is 0.11 m and home
landing error 0.18 m. Fresh motor-based delivery confirmation, camera through
disarm, decision-input isolation and preserved source/runtime hashes pass.
Search QR/red detector delivery rates are 17.9192/17.9508 Hz in simulated time,
or 4.4000/4.4077 Hz against host monotonic time. Full evidence:
logs/reliability_render_my_world_s20261003_handover_guard_20261006/grade.json.

Seed 1001 also closed with 22 of 22 checks passing. Flight time is 880.0 s;
minimum native corridor clearance 0.7130100272 m and restricted-zone clearance
1.6248532894 m exceed the unchanged requirements. Payload error is 0.09 m,
home landing error 0.17 m and motor-based delivery inference completes on
attempt 1 after full estimated hook retraction. Camera export has 3096 original
frames plus one playback hold, duration 929.801 s and last real capture
939.05 s. Fresh connected disarm and complete recording pass.

The owned continuation verifies both source-matched acceptances and exact
archives, then passes the complete latest-source offline suite: 1367 passed,
3 skipped in 692.63 s, with all syntax/configuration/frontend checks passing.
Pair closure is logs/reliability_standard_pair_handover_guard_20261006.json.
The completion coordinator repeats the saved
changing-gust/0.4-second physical command-delay cases across seeds 0-5. A
failed diagnostic stops broader qualification and preserves its report. The
prepared following stages are the six-worker 200-case navigation matrix and
sequential full rendered shipped, rotated and split-corridor runs. These stages,
hardware qualification and flights are not yet qualified. All 12 current-source
gust/delay cases fail; broader qualification was not started. Dirty seed 0
contacts at 6.1 s and late seed 1 at 19.0 s. Slower travel and disturbance-based
speed limiting contact at 12.6/13.0 s. The distance-tracking experiment is a
no-op under the existing distance-proportional speed. A scratch-only earlier
position hold/release contacts at 75.9 s and does not complete traversal.
These experiments remain failures. Production code and recorded qualification
helpers remain unchanged. The coupled-condition repair is still open.

Broader baseline characterization ran with six isolated workers
from the exact 756-entry source archive qualified by both standard seeds and
the latest complete suite. The snapshot's decision and fixture imports were
checked to originate within that snapshot. This preserves a fixed source
while agents diagnose the coupled failure; it cannot qualify a later repair.
The initial launch lacked runtime material assets and was stopped. Its setup
failures remain in logs/reliability_navigation_baseline_matrix_20261006. The
asset-complete closure is logs/reliability_navigation_baseline_matrix_assets_20261006.
The 200 requested combinations include 20 invalid editor_test combinations
(outbound corridor overlaps take-off pad) and 20 unchanged off-axis combinations
classified as geometrically blocked at 0.70 m. These are not traversal passes.

Owned continuation: logs/reliability_standard_pair_continuation_owned_20261006.
Owned completion: logs/reliability_remaining_qualification_owned_20261006.
Completion report: logs/reliability_remaining_qualification_20261006/report.json.

## Patched moving return passed; first full standard launch record

The patched moving return passes all seven focused checks. Native minimum
clearance is 0.7093870740 m, far exit 136.994 s, fresh FCU disarm 143.644 s,
and final real camera capture 144.3 s. Actual entry speed is 0.7591 m/s.
Archive verifies 756 source/helper entries and 53 runtime assets, owned job
exit 0. Recording and PASS.md:
logs/reliability_render_return_handover_guard_moving_20261006.

The full standard mission is now starting with calm conditions, seed 20261003,
the frozen motor calibration and current patched source. Output:
logs/reliability_render_my_world_s20261003_handover_guard_20261006.
Owned job: logs/reliability_standard_s20261003_handover_guard_owned_20261006.
All source and qualification helpers are frozen until evidence closes.

An immediate owned continuation waits for the first owned run's successful
closure and verified full acceptance. It checks the source archive and every
current source/helper hash before starting seed 1001, then verifies both full
acceptances before running the whole offline suite. Any failure or source
change stops the chain. Broader campaigns are not automatically started.
Owned continuation: logs/reliability_standard_pair_continuation_owned_20261006.
If stopping work, stop this continuation and the active rendered job using
the verified owned launcher. The continuation never kills unrelated processes.

The failed-acceptance gate was exercised and refuses continuation. This queue
does not qualify either seed while they are pending, and it does not qualify
hardware. Source remains frozen through both renders and the queued suite.

At this launch checkpoint, seed 1001, the complete current-source offline suite
and broader campaigns were pending. The preserved off-axis world remains an infeasibility
regression. Changing-gust control remains unqualified. Hardware and flights
are deferred. The older 1340-test full pass qualifies its archived source;
the current observer patch passes 34 related controller tests.

## Moving return failed; handover observer repair under validation

The closed moving trial fails clearance and traversal. Minimum native clearance
is 0.6715945852 m; recovery exhausts at 130.213 s. Entry speed is 0.7913 m/s
versus 0.3149 m/s in the earlier full failure, so this is a faster-entry test.
It records fresh connected disarm at 136.933 s and camera through 137.75 s.
Archive verifies 756 entries and 53 runtime assets. Failure details and recording
are preserved in logs/reliability_render_return_measurement_time_moving_20261006.

Three captured-controller regressions reproduce false disturbance and shortened
handover stopping prediction. Current related checks pass 34 in 5.10 s.
The observer now marks the prior response unknown until its own command's
response can be assessed. Stopping prediction retains measured incoming motion
until a known packet arrives. Build and a matching moving rendered repeat are
next. No clearance requirement or model timing parameter was reduced.

## Moving return trial prepared with stricter landing evidence

The driver and grader false-pass regressions reproduced nine failures and now
pass. Moving/landing/qualification checks pass 27 tests, routing/stage checks
214, and recording/campaign checks seven. The final syntax check precedes
launch. The recorder and full grader now also reject disconnected disarm and
camera timelines ending before actual FCU disarm. These changes follow the
1340-test suite snapshot; that full pass qualifies its preserved source only.

Three agents completed parallel diagnosis, driver preparation and evidence
review before hitting the account usage limit. The primary is continuing.
The moving run output is planned as
logs/reliability_render_return_measurement_time_moving_20261006.
No current-source rendered pass or broader campaign pass is claimed.

## Full measurement-time suite passed; moving validation driver under review

The full frozen-source suite passed 1340 tests, with 3 real-corpus skips,
in 869.56 s. Python/shell syntax, XML/YAML and frontend type-check/build pass;
owned job exit 0. All 755 snapshotted entries remain unchanged. Report:
logs/reliability_full_measurement_time_report_20261006.json.

The focused-validation driver is now being extended and independently reviewed
with a moving GateAdvance handover. Its stationary default remains available.
This addition is after the whole-suite snapshot; its separate focused tests
and syntax checks are required before launch. Drone controller/planner source
remain frozen. The current failure's recorded FCU entry is preserved in
return_entry_bannerfix_20261003.json. No live simulator is running yet.

Two scratch proactive-hold trials maintained >1.06 m physical clearance for
20 s, but withheld traversal. Certificate-only variants still contact.
The hold uncertainty envelope is unqualified and no production hold policy
has been installed. Current-source rendered acceptance and campaigns remain
gated. Hardware and staged flights remain deferred.

## Parallel diagnosis and full suite: return remains unqualified

The bannerfix full run failed return at 896.0 s/STUCK x=13.19. Independent
corridor minimum 0.684245767 m violates 0.70 m. Recording ended armed in RTL
at 929.515 s; its exported 919.951 s video is partial. Six acceptance checks
fail. Exact 752-file archive and 53 runtime assets verify. FAILURE.md preserves
the complete result, including the recording cut and source provenance.

Three agents now work on diagnosis, launch/campaign preparation and evidence
review/full tests. A verified FCU sample-time mismatch is fixed; three archived
regressions fail in 0.89 s and 31 related current checks pass in 4.94 s.
Avoidance rebuilt in 29.3 s. The timestamp mismatch explains only part of the
recorded response residual; no rendered return fix is claimed. Source/tests
are frozen for logs/reliability_full_measurement_time_20261006.log in owned
job logs/reliability_full_measurement_time_owned_20261006, domain 221.

A task-scoped detached launcher passed harmless client-exit and scoped-stop
tests. It will be used for future recording runs; forced WSL shutdown survival
is unverified. The next focused return will use the current failure's recorded
FCU entry. No live simulation is running while full offline checks execute.
Campaigns remain gated. Hardware and staged flights remain deferred.

## Oblique-banner regression fixed; fresh full standard run started

An actual return-camera frame reproduced a 0.82-aspect rejection: the new
regression failed in 2.47 s. A measured aspect floor of 0.8 accepts that view
with the existing lettering/area/colour checks. All 209 banner identity, text,
sweep and orbit regressions pass in 16.55 s; perception_banner rebuilt in
18.5 s. No lidar square-up or clearance requirement changed. The full calm
seed 20261003 bannerfix recording is running on frozen production and helper
source. Both full current-source standard seeds remain required for campaigns.
The earlier 1336-test full-suite pass predates this banner change; a new full
suite is required after the targeted rendered fixes pass. Hardware remains
unqualified. Issue 19 and the archived failure preserve the diagnosis.

## Current full standard run closed: 21 checks pass; flight time fails

The source-frozen seed 20261003 receipt-model run completed and disarmed.
Independent grading passed 21/22 checks; the sole failure is 965.0 s flight
against 900 s. Corridor minimum 0.723653986 m, red-zone minimum 1.635075236 m,
fresh motor-qualified delivery and navigation input isolation all pass.
All 267 navigation decisions used fresh FCU EKF velocity, maximum age 0.079 s.
The 1014.851 s video decodes through disarm and exact 752-file source archive
and 53 runtime assets verify. FAILURE.md records the complete result.
Return-banner search delay is being reproduced from actual recorded frames.
No full current-source acceptance pass is claimed; campaigns remain gated.

## Current full standard run: delivery confirmed; return gate search pending

The source-frozen seed 20261003 run confirmed delivery on attempt 1 at
696.801 simulated seconds. Fresh stable motor effort was 0.40658325 after
estimated hook payout reached zero. Visual ground support was not inferred;
this is motor-priority confirmation, not dual-channel corroboration. The
navigation-time decision-input audit passes. The partial independent snapshot
at 514.885 s measured restricted-zone clearance 1.635075236 m and outbound
corridor clearance 1.438356472 m. These are partial results, not a full pass.
Return gate search, return traversal, disarm, final independent grading and
the unchanged 900 s flight-time check are still pending. Production and all
recording/qualification helpers remain frozen.

## Current full suite passed; standard seed 20261003 running

All 1336 offline tests passed, with 3 skips, in 680.27 s. Python/shell syntax,
XML/YAML and frontend type-check/build passed. Report:
logs/reliability_full_fcu_velocity_20261006.log.

Full calm standard mission logs/reliability_render_my_world_s20261003_receipt_model_20261006
is running on the source that passed the focused rendered return. Production,
recording and the four qualification helpers are frozen. Both full standard
seeds must pass all independent checks before the campaign gate opens.
The frozen motor profile and three-attempt retract-and-continue policy are
unchanged. No current full-mission pass is claimed yet.

## Focused rendered return passed; current full offline suite running

logs/reliability_render_return_fcu_velocity_20261006 passed all six focused
checks. It reached the observed far exit at 132.467 s, maintained independent
clearance 0.739236132 m, completed the full return below walls and disarmed.
Input isolation passed. Full 131.551 s video decodes through disarm; 752 source
files and 53 runtime assets verify in the exact archive. This qualifies the
focused return only. Full source-matched standard seeds and campaigns remain
pending. Hardware and staged flights remain deferred.

Current full suite logs/reliability_full_fcu_velocity_20261006.log is running.
After it passes, freeze this source through standard seed 20261003 and seed
1001 full rendered runs. The older failed records and archive-qualified passes
remain preserved. Coupled delayed-gust failures are not qualified.

## FCU-velocity rendered return running

logs/reliability_render_return_fcu_velocity_20261006 is the next focused repeat.
The receipt-model trial closed and failed at 0.687308717 m; complete video and
751-file archive verified. Fresh onboard EKF velocity now takes priority over
pose differencing in braking, and stale/invalid received velocity holds flight.
Six velocity guards pass in 2.71 s; related 34 transport checks pass in 60.17 s
and avoidance rebuilt. Production and qualification helpers are now frozen.
Issue 18 tracks this change. No rendered fix or full current-source pass is
claimed. Broad campaigns remain gated; hardware and flights remain deferred.

## Receipt-model rendered return running

logs/reliability_render_return_receipt_model_20261006 is the repeat focused
return on the same world and recorded FCU starting fixture. Production,
recording and the four qualification helpers are frozen. Yaw-aware observer
and queued-command regressions pass. The related corrected-transport selection
passed 34 tests, with 9 deselected, in 60.68 s; avoidance rebuilt in 17.3 s.
The earlier controller selection passed 61 tests in 394.26 s and rebuilt four
packages before the physical test-fixture correction. Full current offline
qualification and full rendered standard seeds remain pending.

Corrected receipt-physics delayed-gust probes still fail: dirty seed 0 contacts
at 6.05 s, sampled minimum 0.410391157 m; late seed 1 contacts at 7.85 s,
sampled minimum 0.403685054 m. New probe reports include actual source hashes
and command-basis provenance. No coupled-gust qualification is claimed.

## Return diagnosis and yaw certificate change

The focused rendered return reproduced recovery exhaustion and failed at
0.648668474 m clearance. Complete video through disarm and exact source are
archived. A separate real-publication regression demonstrated that the old
translation certificate omitted the yaw command. It failed in 1.76 s before
and passes in 2.07 s after the yaw-aware change. Issue 17 tracks validation.
Broad corridor checks and rebuild are running. No rendered fix is claimed.
The 1323-test suite below was before this latest change; rerun qualification
is required. Delayed-gust contact failures remain unresolved under issue 15.

## Fresh current-source standard run failed

The fresh calm seed 20261003 closed and disarmed. ReturnCorridor reported
STUCK; independent minimum clearance was 0.680769329 m. Four flight checks
failed. The record has a complete 932.101 s decoded video and verified archive
of 750 source files and 53 runtime assets. Motor-based delivery qualified,
camera ground support remained inconclusive, payload error 0.11 m. QR/red
rates were 17.678673/17.764060 per simulated second and restricted-zone
clearance was 1.641411843 m. Issue 16 tracks diagnosis. The campaign gate is
closed. The previously passing two standard runs qualify archived source.

The first simplified closed-loop standard return passes, so it is not yet a
reproduction of the rendered failure. No production fix is claimed.

## Previous running update, now superseded

`logs/reliability_render_my_world_s20261003_gustfix_20261006/` is the fresh
full standard calm run for the changed controller. Source and the four
qualification helpers are frozen. The onboard observer reached DONE on
attempt 1 at 683.8 s after full estimated stow, using stable motor effort
0.4068905 below the unchanged 0.415636489 threshold. Camera ground support
was inconclusive; no dual-channel claim is made. Separate post-flight truth
comparison and raw-output qualification remain for the closed-run grade.

The aircraft is in RETURN_GATE_SEARCH. Independent live minima through search
are 1.246449667 m corridor clearance and 1.641411843 m red clearance. QR/red
delivered rates at that snapshot are 17.56044/17.65028 per simulated second.
Initial and activated-navigation input audits pass. Complete return, landing,
disarm, video export and all 22 checks are still pending.

After this closes and qualifies, run standard seed 1001 on the same source.
The prepared matrix wrapper points to both `*_gustfix_20261006` directories;
the strengthened gate rejects old-source records. Broad navigation and three
additional rendered fixture runs have not started. Physical-delay/gust failures
remain open under issue 15. Hardware and staged flights remain deferred.

## Offline suite passed; fresh rendered qualification next, 2026-10-06

All 1323 current offline tests pass, with 3 skips, in 689.73 s. Python/shell
syntax, XML/YAML, frontend type-check and production build pass as well.
Full report: `logs/reliability_full_changing_wind_20261006.log`. The 117-check
geometry/slalom/stress/delay selection also passes in 402.02 s.

Two additional coupled physical-delay/gust probes fail and remain open under
issue 15. Rejected longer-forecast and raw-path experiments were local probes
only and are preserved. They did not change production. No combined delayed-
gust or worst-condition qualification is claimed.

Four packages rebuilt. Fresh full standard rendered seeds 20261003 and 1001
are next for the changed disturbance certificate. Both must qualify the
current drone source before the campaign gate can open. The first two passing
recordings below remain valid for their exact archived source.

## Gust diagnosis and qualification update, 2026-10-06

The first two full targeted passes below qualify their archived source.
Subsequent offline work found the two remaining gust failures plus ten
invalid-radius yaw fixture failures. The fixture is corrected without changing
its assertions. The full report has 1305 passed, 12 failed, 3 skipped; syntax,
XML/YAML and frontend checks passed.

Measured-trend motion certification now fixes the minimized dirty-lidar gust
case: minimum 0.778495053 m, compared with contact before the fix. The real
publication regression failed before the change and 103 related checks pass
afterward. Broad weather and offline reruns are in progress. This avoidance
change requires fresh rendered qualification; the earlier source archives,
recordings and passing grades remain intact. Campaign source is not frozen yet.

## Both full targeted acceptances passed, 2026-10-06

Seed 1001 PASSED all 22 checks and disarmed at home, with the same recorded
source and frozen load profile as seed 20261003. Flight 888.0 s, corridor
minimum 0.762468206 m, restricted minimum 1.638205369 m, payload error 0.12 m,
home error 0.17 m. Actual fresh FCU motor outputs qualified release on
attempt 2 after full estimated hook stow. Camera support was inconclusive.
Native contact at 674.832 s and confirmation at 706.0 s are stored separately;
the payload stayed stationary across 292 samples from the first probe to DONE.

QR/red rates were 17.72078/17.78025 per simulated second and 4.14475/4.15866
per host second, latency p95 0.238/0.233 s, invalid captures zero. Initial
and active-navigation audits passed. The 938.101 s camera recording decodes
through disarm. All 747 source/helper files and 53 recorded runtime assets
were hash-verified and archived before subsequent changes. Evidence:
`logs/reliability_render_my_world_s1001_20261006/`.

The targeted gate is satisfied. Broader offline and navigation checks are
next, including the headless transport-delay mismatch and the two remaining
gust regressions. Hardware qualification and flight tests remain deferred.

Headless command transport has since been aligned at 0.4 s and 100 related
checks pass. The first full-suite attempt was interrupted after identifying
20 failures in an old altitude fixture that supplied an invalid zero aircraft
radius. Its assertions are unchanged; adding the production 0.025 m occupied
link radius makes all 108 selected checks pass. The full suite restarted in
`logs/reliability_full_after_fixture_20261006.log`. The original interruption
and Windows launcher failure are preserved in
`logs/reliability_full_after_targeted_20261006.log`. The frontend runner now
executes installed JavaScript entry points with host Node rather than shared
Windows `.bin` launchers. No drone production code changed after the two passes.

## First full targeted acceptance passed, 2026-10-06

Standard `my_world.json`, calm seed 20261003 retry 4 PASSED all 22 acceptance
checks and disarmed at home. Independent flight duration 864.1 s, corridor
minimum 0.741457867 m, restricted minimum 1.567421444 m, payload error 0.15 m.
Actual fresh FCU motor outputs qualified release after full estimated stow
on attempt 1. The provisional probe was used; camera support was inconclusive,
so no dual-channel confirmation is claimed. Native payload movement from
probe through confirmation was zero across 190 samples.

QR/red delivered rates were 17.55376/17.62021 per simulated second and
4.11733/4.13291 per host second; latency p95 0.239/0.235 s, invalid capture
events zero. Both input audits and configuration preservation passed.
The complete 914.051 s video passed decoding through disarm. Evidence:
`logs/reliability_render_my_world_s20261003_retry4_20261006/`.

Seed 1001 is RUNNING with the same production source and frozen motor profile,
in `logs/reliability_render_my_world_s1001_20261006/`.
Broader campaigns remain gated until that full targeted acceptance passes.
Two gust failures and the headless physical command-delay mismatch remain
for the subsequent offline campaign work. Hardware and flights are deferred.

## Full standard retry 3 closed, 2026-10-06

The full mission completed, delivered, returned through the unchanged
corridor, landed at home and disarmed. Acceptance FAILS only the 900 s
flight limit: independent duration 927.0 s. Restricted-zone minimum was
1.724529614 m and corridor minimum 0.722613183 m. Fresh actual FCU motor
outputs qualified delivery on attempt 1 after full estimated stow. The
provisional short-probe branch was exercised, then qualified unloaded hover
established touchdown and release. Final camera support evidence was
inconclusive, so no dual-channel confirmation is claimed. Both input audits
and runtime/source preservation passed. Video duration 976.901 s decoded
through disarm. All original evidence is retained in
`logs/reliability_render_my_world_s20261003_retry3_20261006/`.

Return-gate search used 105.983 s and commanded about 2522.7 degrees of yaw.
An empty full-circle minimized actual-stage regression reproduces 1260
degrees in one scan. It failed before the ordering fix, with 89 other
checks passing. Adjacent sequential headings preserve the initial view,
all twelve views, dwell and identity checks. Afterward 213 focused checks
pass in 6.51 s. A new full rendered run is required. Broader campaigns stay
gated on complete acceptance for both requested seeds. Hardware remains deferred.

Four packages rebuilt successfully in 42.5 s. Full rendered retry 4 is now
running in `logs/reliability_render_my_world_s20261003_retry4_20261006/`.
Source, recording and evaluation software stay frozen until it closes.

## Latest return trial and command-delay diagnosis, 2026-10-06

The second focused return retry failed despite progressing roughly 3.3 m.
Independent clearance fell to 0.444372 m. It landed and disarmed, and its
117.451 s camera timeline passed complete decoding. Actual 450-ray lidar,
onboard telemetry, commands and separate native truth are retained in
`logs/reliability_render_return_mount_retry2_20261006/`. No pass is claimed.

The previous focused retry's phase-aligned minimum was 0.937861 m, but it did
not traverse. Certified short bridges between the occupied body-to-sensor
link and nearby grid cells fix the rotated-lattice disconnection. The mount
buffer now subscribes only to static equipment transforms and rejects absolute
vehicle transforms. The final pre-delay regression had 107 passes and two
remaining gust failures. Initial graph snapshots do not replace an audit
after lazy mounting activation; that live snapshot was missed in retry 2.

Onboard command-response fitting estimates 0.37824 s transport delay.
Omitting this delay caused the controller to treat normal response lag as
wind. Two minimized regressions failed, with 88 checks passing, before the
delay fix. After adding a 0.4 s simulation delay to command estimation and
pending-command braking prediction, 90 checks pass. Delayed closed-loop
slalom passes in the final 92-check selection. The intermediate broad set
had 113 passes and two gust failures. No current whole-suite pass is claimed.
The fit is approximate and does not qualify real aircraft response. Another
unchanged standard-world return trial passed in
`logs/reliability_render_return_delay_20261006/`. Its recorder now captures
configuration and initial plus navigation-time input graphs automatically.
Independent minimum clearance was 0.717000770 m, full traversal stayed below
the walls, and the FCU landed and disarmed. Both input audits passed. The
132.801 s VFR camera timeline passed complete decoding. This focused return
pass does not qualify full mission, search, motor delivery or broader weather.
The rendered loaded-payload hover/drop check also passed on attempt 2.
Touchdown and detachment were inferred separately. Motor and onboard camera
support inference agreed after full estimated stow. Native payload movement
through the probe/stow was zero. Both input audits passed, and the 173.901 s
video decoded fully. The unstable provisional branch was not used.
An early transient unnecessarily consumed attempt 1. Its new regression
failed before the candidate-clear fix; 199 focused checks pass afterward.
Frozen thresholds and the three-attempt stow/continue policy are unchanged.
The final full standard seed-20261003 rendered mission is running in
`logs/reliability_render_my_world_s20261003_retry3_20261006/`. Its source,
frozen motor calibration, driver, recorder and qualification helpers stay
unchanged through recording closure. Acceptance now requires actual fresh
motor outputs at confirmation, both input audits, preserved runtime/source
configuration and verified video through disarm. An unconfirmed three-attempt
continuation remains valid mission policy but cannot qualify delivery success.
Full rendered acceptance remains pending. Hardware and staged flights remain
deferred; broader campaigns remain gated on both requested full rendered passes.

## 2026-10-06 continuation

No targeted full rendered acceptance pass is established. Broader campaigns
remain gated. Hardware and flight qualification remain deferred.

The seed-20261003 retry 2 closed and disarmed at home. Its verified camera
timeline is 992.951 s. Search exclusion clearance was 1.72860 m; return
clearance was 0.54835 m and failed. All original failure evidence is retained.

The first focused return trial also failed. Registration now uses the onboard
lidar transform and full capture attitude, but a narrow unobserved link from
aircraft centre to the forward-mounted lidar disconnected the local graph.
The fix admits only that already occupied link, capped by aircraft radius.
Blind reverse and sideways travel remain blocked, and every accepted segment
still requires 0.70 m plus discretisation margin. The trial's initial descent
also touched the banner, so the next fixture descends outside the gate before
crossing underneath. This setup correction does not change the course.

The restored original geometry suite and new registration/footprint tests
passed 77 checks. The subsequent stress suite found three split-corridor
gust failures, with 83 checks passing. A replay showed rejected predictive
wind compensation falling back to raw zero. Current-disturbance cancellation
is now tried only when the same complete motion check certifies it. Its
focused regression failed before the fix. Braking prediction now includes its
response tail and bounds deceleration at 0.5 m/sÂ². That rerun passed 100 checks
and failed two gust cases, tracked in issue 10. A new regression demonstrates
that lateral braking can be certified without predicting masked reverse
motion. Component-wise braking candidates now pass all 82 geometry/registration/
clearance checks. Their stress rerun is pending. No rendered pass is claimed.

Delivery retry observation timers reset separately on every attempt. Sustained
provisional motor unloading near estimated reach can command a bounded short
probe, without confirming touchdown or detachment. Stable qualified unloaded
hover is still required after the probe and after full estimated stow. The
frozen calibration threshold is unchanged. All 197 focused delivery checks
pass; rendered qualification of this change is pending.

## Current rendered retry 2 findings

The full standard seed-20261003 retry 2 failed at the return corridor. Search
maintained independent red clearance of 1.7286 m. Outbound corridor clearance
was 0.84279 m. Return clearance fell to 0.54835 m before recovery exhausted
and requested RTL. Full recording closed through disarm and video export.
The return failure is tracked in issue 08. No acceptance pass is claimed.

Delivery reached actual ground contact at 663.653 s in the separate native
contact record. Its onboard confirmation did not qualify stable unloaded
hover. An expired telemetry timer consumed attempts 2 and 3 within 0.4 s;
two minimized timer regressions reproduce the bug before a fix.
The hook fully retracted by estimate at 711.6 s and the mission continued
with delivery explicitly unconfirmed, as required. Frozen load thresholds
are unchanged. Contact disturbance is being evaluated independently; native
contact is never an observer input.

### Rendered acceptance update

The calm seed-20261003 retry failed after delivery: the observer reached motor
confirmation on attempt 1 at t=769.0 s, then the mission node crashed reading
missing camera coordinates for its optional offset report. Operator recovery
landed at the delivery location and disarmed. The complete failed evidence is
under `logs/reliability_render_my_world_s20261003_retry1_20261005/FAILURE.md`.
No return traversal or full acceptance pass is claimed. The camera reporting
guard is fixed; 191 focused tests pass. A new same-world, same-seed run is required.
The broader matrix remains gated on both targeted rendered acceptance passes.
The same-seed failed rerun is retained under
`logs/reliability_render_my_world_s20261003_retry2_20261005/`. Its live graph audit
finds no simulator-truth/contact/attachment subscriptions in the mission, winch
or avoidance nodes. Host-time rates and camera angle feedback are now recorded.
The failed flight's verified timed video is `onboard_sim_time_verified.mp4`,
814.101 s; the capture ledger expects 814.100 s and full decode passes.

## 2026-10-05 implementation and qualification

- Connected lidar/pose planner, capture-time scan registration, hard 0.70 m
  segment checks, observed reverse recovery and signed corridor progress
  are implemented. Narrow-clearance fallback is removed. Diagnostics record
  path, age, clearance, axis progress, braking holds and recovery reasons.
- The unchanged off-axis SHA256 is
  `bd842c00f4918857094f6d669910142143903cf5c1385b686c98c011bc2b3537`.
  `logs/offaxis_clearance_audit_20261005.json` proves the 0.70 m inflated
  polygons join both walls. Grid bottlenecks remain 0.45 m at 5 cm and
  0.4375 m at 2.5 cm. This is geometrically infeasible, not a traversal pass.
- `logs/corridor_strict_stress.log`: 21 tests pass at 0.70 m, including
  rotated corridors and gusts. `logs/reliability_final_focus.log`: 409 pass.
- Distinct-frame timing, processing latency, slower-detector speed limits,
  stale-observation holds, capture-time ground projection and measured-pose
  route revalidation are implemented. Search faces each certified detour
  segment before moving. Simulator exclusion coordinates are not inputs.
- The saved restricted-zone failure was reproduced at SEARCH_QR 214.38 s,
  minimum clearance 0.29 m. See `logs/restricted_zone_reproduced_20261005.txt`.
- Earlier rendered acceptance used `my_world.json`, calm, seed
  20261003, under `logs/reliability_render_my_world_s20261003_retry1_20261005/`.
  The first attempt stopped before flight and the next observation found a
  fresh WSL instance. Its partial evidence is retained in the original
  directory with `INTERRUPTED.md`. Neither attempt is yet a pass.
  Seed 1001 follows only after targeted acceptance passes.
- The full Python suite passed 1,267 tests, 3 skipped, under
  `logs/reliability_full_final.log`. Python and shell syntax also passed.
  The interrupted final stages were run separately: project XML/YAML,
  TypeScript and production build passed in
  `logs/reliability_remaining_offline.log`. Earlier suite and wind failures
  are retained. Do not use `logs/reliability_full_suite.log` for qualification.
- The four changed ROS packages build. Linux-native GCS type checking and
  production build pass, `logs/reliability_frontend_linux.log`.
- The recorded runner keeps full camera, commands and onboard telemetry
  through disarm, with separate payload and native aircraft truth. The
  matrix runner gates on both targeted passes and separates object-level
  navigation from rendered perception and motor delivery qualification.
- Broader campaigns and rendered shipped/rotated/split acceptance remain
  pending. No campaign or rendered acceptance success is claimed yet.
- Motor-priority delivery and three-attempt full-stow/unconfirmed-continue
  behaviour remain in place. Physical claw work is unchanged.
- `docs/HARDWARE_QUALIFICATION_RECORD.md` records all hardware as unqualified
  and all staged flights as deferred. No physical qualification was performed.

## Historical progress, 2026-10-03

## Inspected

- Base commit `210daa7`; existing uncommitted work preserved.
- Historical root handoff is superseded by current code and logs.
- Latest stored nine-world campaign passed 7/9; both failures reproduced or
  isolated before editing.
- Physical claw findings remain in `docs/hook_physics.md`: uneven loading
  loses the payload; even loading can carry it but stow may grab it again.
  Full-mission simulated payload release does not qualify that CAD mechanism.

## Continued

- Reject clipped banner geometry before placing the return stand-off.
- Retain an expired stall reference until measurable movement starts a new
  window, allowing existing backoff/STUCK recovery to run.
- Three regression tests cover the false range, stationary visible-gap
  recovery, and recovery after actual movement.
- Targeted final checks: 95 passed (`logs/continue_targeted_20261003.log`).
- Rotated seed 1 and shipped seed 1: 2/2 COMPLETED and independently PASS,
  zero contacts and fence breaches (`logs/continue_fix_20261003`).
- Off-axis seed 1: bounded STUCK failure after all three backoffs. Still FAIL
  as a mission; its original geometry was preserved.

## Additional closed-loop validation

- Rotated seeds 2-3 and current `my_world` seeds 2-3: 4/4 COMPLETED and
  independently PASS, zero contacts and fence breaches.
  Evidence: `logs/continue_regression_20261003/summary.json`.
- Together with rotated/shipped seed 1, 6/6 successful mission runs in this
  continuation. All used the worlds' own calm presets; these are different
  mission seeds, not a new random/worst-conditions qualification campaign.
- Both current-world runs reported delivery UNMEASURED in mission telemetry
  because the pad was absent from the release frame. Payload ground detection
  was confirmed, and the independent ground-truth grader passed placement.
- Initial full offline run: 1218 passed, 3 skipped; Python/shell syntax and
  XML/YAML checks passed (`logs/continue_offline_20261003.log`).
- Final full offline run: 1220 passed, 3 skipped; Python/shell syntax and
  XML/YAML checks passed (`logs/continue_final_offline_20261003.log`).
  The runner used `--quick`; the unchanged GCS frontend was not rebuilt.

## Remaining

- Off-axis chicane planner capability, issue 03.
- Re-run rendered Gazebo + ArduPilot SITL with the current code. The last
  saved `my_world` rendered mission completed but failed restricted-zone
  grading. The interrupted detector-rate pacing change targets that defect;
  headless passing missions do not verify its rendered-camera timing.
- Physical claw retention and release/stow, then real bench qualification.
- Pi, sensors, real-camera and flight qualification in `docs/FIELD_READINESS.md`.

## Recorded rendered rerun - 2026-10-03

- Ran the last failed world `my_world_offaxis.json`, seed 1, calm, target B,
  unchanged, in rendered Gazebo Harmonic with ArduPilot SITL.
- FAILED at 796.8 simulated seconds: return recovery backed out through the
  entrance; `ReturnCorridor` rejected the mouth as the far end. RTL then
  landed and FCU disarmed. The full airborne interval was 780.0 seconds.
- Full-flight independent grade: FAIL. One restricted-zone entry during
  SEARCH_QR, incomplete return traversal, and RTL over the corridor. No
  obstacle contacts, tilt events or geofence exits. Payload error 0.17 m;
  landing error 0.03 m. The rendered pacing defect remains open.
- Video: `logs/custom/my_world_offaxis_calm_s1.mp4`, 789.367 seconds,
  H.264 1280x720 at 30 fps; one continuous segment, measured wall/sim
  speed correction x3.597, fast-start remux, complete decode successful.
- The original live runner stops shortly after the mission result. Its
  grade therefore cannot assess the later RTL landing. A read-only observer
  held the recorder controller until disarm; the encoder and flight kept
  running. `*_full_track.csv` adds only observer samples after the original
  track's final timestamp; `*_full_grade.txt` grades that complete flight.
- Evidence: `logs/custom/my_world_offaxis_calm_s1_manifest.json`,
  `*_stack.log`, `*_layout.json`, `*_disarm.json`, `*_full_track.csv`,
  `*_full_grade.txt`, and `*_video_decode.log` (empty, decode exit 0).
