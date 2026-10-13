# Finish the interrupted custom-world reliability work

Inspected on 2026-10-03 at commit `210daa7`, with existing uncommitted
banner recovery, green-ground modelling, detector pacing and world changes.
Those changes were preserved.

The latest saved campaign, `logs/campaign_spec/summary.json`, completed and
passed 7 of 9 worlds. `rb_rotated` failed return alignment after placing a
clipped banner at a fabricated 5 m range. `my_world_offaxis` stalled in the
return corridor until battery-critical RTL.

## Acceptance

- A clipped banner does not provide a position for the return stand-off.
- The rotated and shipped worlds complete and pass independent track grading.
- A stationary aircraft with a visible gap reaches the existing bounded
  recovery ladder instead of resetting the stall every progress window.
- Movement after a stall starts a new progress window.
- Preserve the off-axis world as a failing geometry fixture. Do not widen it
  or reduce aircraft clearance to make its grade pass.
- Record headless, rendered SITL and physical-mechanism evidence separately.

Implementation and evidence are in [status.md](status.md) and the numbered
[issues](issues/) directory.

## Current scope, 2026-10-05

The requested clearance is 0.70 m throughout planning and recovery. The
unchanged off-axis world is an infeasibility regression if its inflated
obstacles block the lane. A traversal pass cannot be claimed for it.

Search decisions must use fresh onboard camera detections. Measure distinct
capture times, processing latency and delivered QR/red rates; bound speed
by the slower detector and braking distance. Revalidate active segments
when exclusions change, stop unsafe commands and replan from measured pose.

Rendered targeted acceptance is `my_world.json`, calm, seed 20261003 then
1001. After both pass, run seeds 1-5 across all world fixtures in calm,
field, worst and random conditions, and rendered standard, shipped, rotated
and split-corridor trials. Record through disarm and retain separate truth.
Headless navigation cannot qualify rendered perception or motor delivery.

Hardware and flight work remain deferred. Preserve motor-priority delivery,
three unsuccessful attempts followed by complete stow and unconfirmed
mission continuation, and the existing physical claw.
