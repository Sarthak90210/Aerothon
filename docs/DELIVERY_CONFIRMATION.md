# Delivery confirmation from onboard observations

The drone commands lowering, stopping, short retraction, retries and full
retraction. Its delivery observer uses only the onboard camera and MAVROS
flight-controller observations. Gazebo's contact-release component does one
thing: detach the payload on contact with the ground or a target surface.
It has no ROS publisher and sends no contact or attachment state to the drone.

## Evidence and limits

The camera estimates payload range from its longest visible edge, calibrated
field of view and pixel size. Distinct capture timestamps are required.
Ground proximity is inferred by comparing this range with aircraft altitude;
it is not a contact measurement. The calculation assumes the configured
payload edge is visible, nadir viewing, stable flight and the local altitude
datum being near the target surface. Pose/shape errors can invalidate it.

The primary decision channel uses mean squared normalized FCU motor PWM as a hover
effort proxy. This is neither measured motor current nor measured thrust.
IMU acceleration, tilt, horizontal speed and vertical speed reject unstable
flight intervals. Battery current is not substituted for individual motor
current. No calibrated effort separation means no confirmed delivery.

Winch travel is integrated from commanded speed; there is no line encoder or
stow limit switch in the current interface. `payout_estimate_m` and
`payout_basis` expose this explicitly. `ground`, `released` and `hook_open`
are unknown at the winch interface. `release_requested` records intent only.
The delivery observer exposes `touchdown_inferred`, `detachment_inferred`
and `delivery_confirmed` separately on `/mission/delivery_observation`.
`load_reduction_inferred` reports sustained calibrated unloading independently
of camera agreement. Unloading alone cannot distinguish ground support from
detachment. `continued_unconfirmed` records completion of the fallback path.

## Sequence

The observer checks loaded hover against a frozen calibration, commands
up to 0.6 m estimated initial deployment if the stowed payload is occluded,
then requires camera tracking for further lowering. Initial deployment is
also limited to remain at least 2 m above the estimated ground. It requires
stable, sustained unloaded motor effort to infer touchdown and start the
release test. Camera ground-range evidence is supporting information, and an
incorrect range or missing frame cannot veto the primary load signal.
It commands 0.25 m estimated retraction and checks whether load returns.
Returned suspended load triggers another lowering attempt. After full estimated
retraction, another sustained unloaded-hover check is required for confirmation.
Motor unloading does not directly measure contact: touchdown and delivery are
inferences. Camera support remains separately reported, and the final mission
result names the motor-based confirmation basis instead of claiming visual proof.
There are three total attempts and a 300-second simulated observation budget.
After the third unsuccessful attempt the drone fully retracts the hook, then
climbs and continues the normal mission with delivery unconfirmed. Camera loss
or inconclusive load evidence does not block this fallback retraction. Recovery
has a separate 45-second retraction timeout; a winch fault or incomplete recovery
still fails the stage. Retraction completion remains estimated from commanded
travel, because no encoder or stow switch is present.
Normal success uses the calibrated motor signal through retraction. Final landing reports
`DELIVERY_UNCONFIRMED` when the fallback was used, even though mission navigation
continued. Missing calibration or loaded baseline remains a pre-delivery failure.

## Calibration and demonstration

Run from WSL, with ROS and the workspace installed. The trial wrapper refuses
to interrupt another running simulator and owns its stack lifetime.

```sh
bash scripts/run_delivery_trial.sh loaded logs/delivery_loaded
bash scripts/run_delivery_trial.sh unloaded logs/delivery_unloaded
python3 scripts/calibrate_delivery_load.py \
  --loaded logs/delivery_loaded/effort_samples.json \
  --unloaded logs/delivery_unloaded/effort_samples.json \
  --out logs/delivery_load_profile.json
bash scripts/run_delivery_trial.sh delivery logs/delivery_trial \
  logs/delivery_load_profile.json
```

The unloaded calibration fixture starts without an attached payload. That is
an experimental initial condition, not an onboard detector input. The normal
fixture carries the payload; only physical surface contact triggers detach.
Calibration requires at least 30 stable observations per fixture and disjoint
three-standard-deviation effort bands. Profiles are frozen before delivery.

Set `AEROTHON_DELIVERY_CALIBRATION` to the profile's absolute path for normal
mission launches. Configure `delivery_motor_channels`, `delivery_motor_pwm_min`
and `delivery_motor_pwm_max` for the actual motor outputs. The demo defaults
to the CAD C270 field of view and the 0.10 m payload edge. These must match the
aircraft, and a profile from one vehicle/settings cannot qualify another.

Each trial saves `onboard.jsonl`, annotated onboard-camera video and
`result.json`. `evaluation_truth.jsonl` is recorded by a separate observer
that never publishes or commands anything. It is only for evaluation.
The full mission sequence remains idle during these hover/drop trials.

## Verification

`sim/test_delivery_observer.py` covers motor-priority decisions and supporting camera evidence,
distinct frames, stale telemetry, unavailable camera, retries, exhaustion,
calibration rejection and surface-contact filtering. Payload/winch tests
assert that commanded release and inferred travel cannot certify delivery.

Live acceptance requires separate qualified hover traces, a successful
recorded release trial and independent evaluation of payload motion. Passing
offline tests alone does not establish that acceptance or real-flight readiness.
