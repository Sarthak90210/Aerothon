# Hardware qualification record

Status: deferred. Simulation results do not qualify any item below.

Use a separate record for each hardware configuration. Record the date,
operator, software commit and hashes, Pixhawk firmware and parameters,
Pi image, camera calibration, airframe mass and actual payload mass.
Keep propellers removed throughout initial electrical and actuator checks.
No wiring assignment, servo limit or winch rate is assumed by this document.

| Item | Measurement and evidence required | Result |
| --- | --- | --- |
| Pi | Boot log, installed dependencies, mission restart, CPU temperature, sustained processing rates and latency under the complete stack | Unqualified |
| Camera | Actual device, resolution, intrinsics, field of view, capture timestamps, dropped frames, QR and restricted-zone rates under expected lighting | Unqualified |
| Lidar | Mounting direction, left/right/forward signs, shadow sectors, range against measured targets, capture age and dropouts | Unqualified |
| Camera servo | Measured wiring and supply, commanded and actual angles, travel limits, slew time and repeatability | Unqualified |
| Winch | Measured payout and retraction rates with the real payload, travel limits, full stow, commanded travel error, emergency stop | Unqualified |
| Pixhawk | Measured connector pins, voltage levels, grounds, UART settings, link loss and reconnection logs | Unqualified |
| Velocity response | Separately measure command transport delay, response time after arrival, braking acceleration and pose/velocity noise, with the loaded and unloaded airframe | Unqualified |
| Motor/load signal | Loaded and unloaded hover trials, actual available current channel, motor-output calibration, repeatability and separation from motion disturbances | Unqualified |
| Failsafes | Props-off command/link loss, stale camera/lidar/FCU data, low battery, restart and stop behaviour | Unqualified |

For each row retain the raw measurements, configuration, timestamped commands,
sensor readings and observed response. Record a pass criterion before the
trial and the reviewer who accepted the result. A missing measurement remains
unqualified. Freeze a load profile only after separate loaded and unloaded
trials; acceptance trials must use that frozen profile.

Claw retention and release remain separate physical work. Delivery software
uses motor evidence first. After three unsuccessful attempts it retracts the
hook fully and continues with delivery marked unconfirmed.

## Measurement sheet

Copy this sheet for each device or trial. Leave unknown measurements blank.

| Field | Measured value or evidence |
| --- | --- |
| Date, operator and reviewer | |
| Device model, identifier and firmware | |
| Software commit, source hashes and configuration | |
| Connection pin, measured voltage and reference ground | |
| Command, units and intended response | |
| Timestamp source and alignment measurement | |
| Measured orientation, position or travel | |
| Measured rate, latency, repeatability and uncertainty | |
| Loaded/unloaded mass and conditions, where applicable | |
| Pass criterion recorded before the trial | |
| Raw log, camera record and measurement-file paths | |
| Observed result, failures and reviewer decision | |

Props-off electrical checks cannot establish loaded/unloaded hover effort.
That signal remains unqualified until separate actual hover trials provide
repeatable separation. Record servo angles and winch travel with an external
measurement when the installed mechanism has no position sensor.

The current simulation uses a 0.4 s velocity command delay after a rendered
FCU identification estimated 0.37824 s. This does not qualify the Pi-to-Pixhawk
link or the real airframe. Align command and FCU timestamps before fitting
transport delay and response time separately. Record uncertainty and repeat
the measurement loaded and unloaded before selecting hardware parameters.

## Flight stages

Flights remain deferred until bench evidence is reviewed. Review each stage
before advancing. Record the configuration, site, conditions, payload,
flight-controller log, onboard camera, commands, inferred decisions and
observed outcome. A simulation pass is not a flight-stage pass.

| Stage | Evidence to review before advancing | Status |
| --- | --- | --- |
| Hover | Stable pose and motor telemetry, calibrated load assessment, hold and abort response | Deferred |
| One gate | Camera/lidar signs, alignment, minimum clearance and controlled stop | Deferred |
| Outbound corridor | Connected path, clearance, progress and stale-observation holds | Deferred |
| Return corridor | Chicane clearance, observed reverse recovery, exhaustion stop and far-end detection | Deferred |
| Delivery | Real payload lowering, touchdown inference, retraction probe, retained-payload retries, full stow and unconfirmed continuation | Deferred |
| Full mission | Complete recording through landing and disarm, all mission requirements and independent review | Deferred |
