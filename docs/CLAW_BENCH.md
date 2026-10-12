# Physical claw bench record

Status: not performed. No mechanical redesign has been selected.

The previous contact simulation lost an unevenly loaded payload and lifted
a released payload again during stow. Those failures are recorded in
`docs/hook_physics.md`. A simulated release does not qualify the real claw.

## Measure the assembly first

Record units, date, photos and whether each dimension is measured or from CAD.

| Measurement | Actual value |
|---|---|
| Payload mass and dimensions | pending |
| Attachment shape, orientation and dimensions | pending |
| Eye centre to payload bottom when carried | pending |
| Jaw pocket width, depth and lateral support | pending |
| Jaw/joint play and material | pending |
| Ground to loaded eye, aircraft resting on its gear | pending |
| Payload bottom to ground, line fully stowed | pending |
| Winch controller/output, supply and wiring | pending |
| Payout/retract speed with this payload | pending |

Ground clearance equals loaded eye height above ground minus eye-to-bottom
distance. Include the real stowed line length. Agree a clearance margin
before choosing landing-gear or mount dimensions.

## Test sequence

Use a secured bench assembly, props removed, a catch tray beneath the payload
and a reachable actuator power cut. Begin at low height, increasing only
after retention is demonstrated. A person must observe physical motion.

1. Load the actual attachment, remove its support and observe retention.
   Repeat with measured offsets that represent the real loading process.
2. Lower under load, recording line travel and payload motion. Any separation
   before the payload is supported by the tray is a failure.
3. Continue the specified slack travel after touchdown. Record whether the
   jaws clear the attachment without manual assistance.
4. Retract completely with the payload still below the claw. Record any
   renewed contact or upward payload motion. A later fall does not erase a
   re-grab failure.
5. Check the latch reset, reload and repeat. Record the agreed cycle count
   and every attempt, not just the successful ones.
6. With the aircraft resting on its gear, load and stow the payload. Measure
   the minimum payload clearance and verify retention before any lift.

Before powered testing, confirm the controller/output, travel limits and
power-cut procedure. No actuator commands are supplied by this document.

## Trial record

| Trial | Design revision | Load offset | Retention | Release | Maximum lift during stow | Ground clearance | Evidence |
|---|---|---|---|---|---|---|---|
| pending | pending | pending | untested | untested | unmeasured | unmeasured | none |

Agree hold time, offsets, release travel/time, clearance margin, measurement
resolution and number of cycles before recording acceptance. Real actuator
settings must come from measurements, not the simulated defaults.
