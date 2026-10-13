# Verify detector-rate pacing in rendered Gazebo and SITL

Status: ready-for-agent
Resolution: older archived standard seeds passed; current-source full acceptance and broader rendered fixtures pending
Parent: ../spec.md

The two 22-check passes below qualify their archived source. Later controller
changes require a fresh matching pair. The most recent bannerfix run fails
return and complete-through-disarm checks; it does not open the campaign gate.

The last saved rendered `my_world` mission completed but failed
restricted-zone grading (`logs/custom/my_world_grade.txt`). The existing
uncommitted pacing change measures both QR and restricted-zone detector
rates and uses the slower detector when setting sweep speed. Its focused
regression passes; the headless detector publishes at an assumed cadence
and cannot qualify the real rendered-processing latency.

Next run, in a non-login WSL shell with system Python and ROS sourced:

```sh
bash scripts/run_recorded_acceptance.sh sim/worlds/my_world.json 20261003 \
  logs/NEW_ACCEPTANCE_DIRECTORY logs/delivery_profile_20261005.json
```

Before launching, inspect existing simulator process groups and reserve the
live stack's ports/ROS domain. The recorded runner refuses another active
simulator, uses an isolated ROS domain and terminates only its owned stack.

Acceptance: COMPLETED plus every independent grading check, including no
restricted-zone entries and at least 1.50 m exclusion clearance, with
distinct capture times, QR/red delivered rates and processing latency.
Record through disarm, with separate native aircraft and payload truth.
Run calm seed 20261003 then seed 1001. Save the rendered track, layout and
stack logs separately from headless evidence.

## Comments

2026-10-03: the requested recorded rerun used the last failed off-axis
world, seed 1, calm, target B. Its complete rendered trace still enters
`restricted_red_zone_3` at simulation t=252.33 s during SEARCH_QR;
closest distance to restricted ground was 0.07 m. Existing detector pacing
is not qualified by this run. Evidence:
`logs/custom/my_world_offaxis_calm_s1_full_grade.txt` and `*_stack.log`.
The standard `my_world.json` acceptance run remains pending.

2026-10-05: Regrading the saved standard-world track reproduced the entry
into `restricted_red_zone_3` at simulation 214.38 s in SEARCH_QR, with
0.29 m closest clearance. Evidence: `logs/restricted_zone_reproduced_20261005.txt`.
The new production pacing counts distinct capture timestamps, requires
both detectors fresh, includes latency and braking, and waits for speed ACK.
Active segments are checked against changed exclusions from measured pose;
a blocked segment cancels the previously streamed destination. A stalled
heading cannot authorize camera-blind travel. Red ground projection now
requires an aircraft pose near camera capture time.
These changes have focused test evidence. They are not yet a rendered pass.
# First targeted full acceptance pass, 2026-10-06

Standard calm seed 20261003 retry 4 PASSED all 22 independent checks.
Restricted-zone minimum 1.567421444 m. QR/red delivered rates
17.55376/17.62021 simulated Hz and 4.11733/4.13291 host Hz, latency p95
0.239/0.235 s, zero invalid capture timestamps. Complete video decoded
through disarm; source/runtime configuration and both input audits passed.
Seed 1001 is running with the same source and frozen profile. Broader
rendered qualification remains pending. See its retained RESULT.md.
