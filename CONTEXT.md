# Context

Domain vocabulary for the AeroTHON 2026 Mission 2 stack. Glossary only — no
implementation detail, no decisions. Decisions live in `docs/adr/`, evidence
lives in `VERIFICATION.md`.

## Arena

**Restricted zone** — the rulebook's term for ground the aircraft may not fly
over. Scored: 10 marks, minus 5 per violation.

**Red zone** — the physical painted ground in the arena. What the camera sees.
A red zone is the *appearance* of a restricted zone.

**Exclusion** — a georeferenced rectangle in local ENU that the lane planner
routes around. What the mission *believes* about a red zone, derived from
confirmed camera observations.

> These three are not synonyms and the distinction is load-bearing. A red zone
> constrains the **airframe**, not the **camera**: flying the camera's
> footprint over red ground is harmless, flying the aircraft over it is a
> violation. Clipping lanes against the camera swath instead of the airframe
> clearance over-clipped the plan and dropped coverage to 0.81.

**Delivery zone** — the area beyond the corridor containing the target pads.

**Delivery-zone boundary** — the closed geographic polygon supplied by the
organisers before flight. It is the authoritative search envelope for the
delivery zone and required mission input.

**Mission-ready boundary** — a delivery-zone boundary that is present, valid
and usable. Without one, the aircraft is not ready to arm.

**Arena geofence** — the organiser-supplied polygon the whole flight must stay
inside (rulebook: "Coordinates for the geo-fence boundary will be provided").
Distinct from the delivery-zone boundary, which bounds only the search. It is
uploaded to the flight controller, read back and enforced before arming;
exclusions are never added to it.

**Bottom-left start** — the lawnmower search always begins at the south-west
(min x, min y) corner of the delivery-zone boundary, whatever point the
corridor let the aircraft out at.

**Free-space window** — the open ground visible to a ranging sensor from one
pose. It describes immediate obstacle clearance, not the delivery-zone
boundary.

## Perception

**Detect** — something of the right kind is present in frame.

**Identify** — that thing is confirmed to be *the* banner, by its colour and
by structure. Stronger than detect. The organisers confirmed the banners carry
no text, so the structure is the **banner border**: a solid colour field inside
a thin white frame. A plain coloured sheet has the colour and can have the
size; it is not framed. Reading lettering is retained as a confirming path for
an arena that happens to have some, never as the requirement.

**Align** — the aircraft has yawed to face an identified banner. The rulebook
scores "detect ... and autonomously align" as one task. Align says where the
nose points, nothing about where the aircraft is.

**Supplied colour** — a banner's shade as the organisers give it, a HEX code
latched on `/mission/banner_colours` and reported by the readiness interlock.
It is a *nominal* colour: wear, shade and exposure move a printed panel, so it
becomes a hue band with a tolerance, never an equality. Without it the
aircraft would be identifying a corridor by a guess, so it is an interlock
item and not a convenience.

**Banner placement** — where a banner is mounted: **suspended** from a rod
between the corridor walls, or **ground** — laid flat in front of the mouth
with its colour facing the sky — or both. A ground banner has no vertical
face, so nothing can square up on it with the lidar, and it is seen by
tilting the camera down rather than looking ahead.

**Alignment pass** — one attempt to align to one banner view. A gate is
approached with one pass per view, the hung board then the ground sheet, so
both banners are used in turn rather than whichever is seen first. At least
one pass is required. The hung view goes first; after it, the ground view is
only **glanced** at (a few seconds at the heading just found), and the second
pass runs only when that glance identified a banner, so a gate with nothing
on the ground is not charged a full sweep. If the hung view identifies
nothing within its budget, the aircraft returns to where that view started
and the ground pass becomes the required one. A gate that only the ground
pass could align to makes the next gate try the ground view first; the hung
view is still the last resort.

**Arena dimensions** — every length the algorithms depend on (corridor,
hall, banner, QR, red zone, payload), entered at the GCS in metres, feet or
inches and applied by rebuilding the mission on the ground. A field no
algorithm reads is still recorded, and marked so. Named sets of them are
**presets**; the built-in ones cannot be overwritten.

**Operator's path** — the only way arena dimensions reach the aircraft, in
simulation as at the competition: a preset saved at the GCS, applied over
the aggregator before START, confirmed by the mission as applied. A run that
passed them as launch parameters has not tested the path the day uses.

**Green and orange banners** — every corridor opening carries one. Green
marks the corridor to use for the current direction of travel, orange the
one beside it that must not be used. The gate search looks for green only;
orange is named when asked about a panel but never aligned to. A hung
banner hangs from a rod between the corridor walls, top at the wall top,
and the aircraft always passes UNDER it. Its height is not given, so it is
entered at the GCS and flown at more than one value.

**Square on** — the aircraft is perpendicular to the banner's face, within
tolerance, at a measured standoff. Stronger than align, and measured by the
lidar rather than inferred from the camera. An aircraft can be aligned while
well off to one side; only a square-on aircraft may advance through the gate.

**Scan** — point the camera at a QR marker and attempt a read.

**Decode** — recover the payload string from a scanned marker. A scan may
fail to decode.

**Match** — the marker in frame is the one the start QR named. Two kinds of
evidence can establish it, in this order:

**Appearance match** — the marker's own printed pattern, rectified off its
four corners and compared cell by cell, is the pattern the start marker
showed. This is the primary evidence, because it is unsettled whether the
competition codes encode anything at all, and a code that encodes nothing
still looks like itself.

**Payload match** — a decoded payload names the same place the start QR did
(`qr_match.identifiers`). Confirming, not required. Decoding is not matching,
and neither is a decode the aircraft never got: what identified a marker is
published alongside the match so nothing can claim evidence it lacks.

**NOT_VISIBLE** — the red-zone detector has no usable ground view, so it
reports nothing about the ground. Distinct from CLEAR, which asserts the
ground was seen and is not red. Collapsing the two makes "no camera" read as
"no hazard".

## Mission

**Start QR** — the marker at the take-off point naming the delivery target.

**Target pad** — a marker in the delivery zone. Exactly one matches.

**Verified target** — a target pad whose payload matched repeatedly while the
aircraft was stationary, which the aircraft then centred over and reconfirmed.
Only a verified target may be used for payload delivery.

**Decode altitude** — the highest altitude the payload marker is still
readable from. Derived from the measured px-per-module floor.

**Sweep altitude** — the altitude the search flies at, set by pad
detectability and capped by the rulebook ceiling.

**Tracking floor** — the lowest altitude at which the whole pad still fits in
frame. Below it, visual lock is geometrically impossible.

**Standoff** — how far short of a target the aircraft stops so the target is
in the camera's field of view rather than beneath it.

## Evidence

**Nominal / shipped arena** — the single arena committed to the repo.

**Randomised arena** — an arena generated from a seed, with the corridor,
delivery zone, pads and red zones moved.

**Arena regression** — the full mission flown across several randomised
arenas. The acceptance test for the perception-driven claim: passing on the
shipped arena cannot distinguish "derived from perception" from "derived from
a constant that happens to agree".

**Custom arena / world spec** — an arena a person placed by hand in the world
editor (`tools/world_editor`), saved as JSON in `sim/worlds/`: take-off area,
the outbound and return corridors (each with its own pose, length, width and
wall height; the return one *linked* beside the outbound one, as in the
rulebook drawing, or placed anywhere), the return corridor's obstacles, the
delivery zone, geofence, any number of red zones, the pads, decoys, the named
target and QR sizes. Unlike a randomised arena nothing about it is chosen by
the code, so it is the sharpest test for a surviving constant. Only the
banners and the take-off pad's internal layout keep their shape.

**Return gate search** — how the aircraft finds the return corridor without
being told where it is: a full turn at the stand-off first (the rulebook
layout ends here, on the first heading), then vantage points along the
delivery zone's edge, nearest the outbound exit first, each looking outward.
A sighting is the identified banner that is not the outbound one (whose
position was recorded on the way out) and is within the near range.

**Team airframe** — the vehicle the simulator flies by default
(`AEROTHON_AIRFRAME=cad`): the team's quad built from its CAD in
`Drone frame/` by `scripts/cad_to_gazebo.py` (meshes and measured mounts in
`models/aerothon_quad/airframe.json`) and `scripts/build_cad_vehicle.py`.
2.0 kg all-up, 2312 980 KV on 9450 props at 4S (4S2P 9000 mAh Li-ion),
Logitech C270 (48.8 deg HFOV) on a tilt servo, LD06 lidar on the raised
front mount, gravity-hook winch. `AEROTHON_AIRFRAME=iris` flies the older
ArduPilot Iris variant.

**Gravity hook** — the team's payload support, lowered and retracted by the
winch. Its physical retention and release behaviour requires bench qualification.

**Contact release** — the simulation fixture's detachment of the payload
when it contacts the ground. This is distinct from the aircraft's inferred
touchdown and detachment.

**Commanded winch travel** — the estimated payout or retraction accumulated
from motor commands. It is distinct from measured hook position.

**Inferred touchdown** — the aircraft's assessment that the payload has
reached the ground from its onboard observations. It is distinct from
simulator contact truth.

**Inferred detachment** — the aircraft's assessment that the payload remains
behind while the hook retracts. It is distinct from an accepted winch command.

**Edge-on orbit** — what both banner searches do when a full turn reads no
banner but did see green: the board is being seen from the side or behind,
where no lettering shows. The largest green region is taken as where the gate
stands (bearing from the camera, range from where it meets the ground or from
its height), and the aircraft flies vantage points round it at search
altitude, facing it, until the lettering reads. It is tried before the blind
relocation pattern and does not count against its budget. An empty heading
ends once it can no longer reach the dwell's hit floor, and the lettering can
be read mid-leg. With no green seen anywhere, a ring of vantage points round
the search's start is the last resort. `banner_orbit.py`.

**Confirmed delivery** — a delivery inferred from qualified, sustained
unloaded motor effort after a retraction probe and complete hook retraction.
Onboard camera observations provide separate payload tracking and visual
ground-support evidence.

**Unconfirmed delivery** — a delivery for which the aircraft lacks sufficient
onboard confirmation. The mission continues after full hook retraction, but
its final outcome remains DELIVERY_UNCONFIRMED.
## Search and navigation

**Routed leg** — a transit between two points, checked against the exclusion
set and detoured around it if the straight line would put the airframe inside
one. Distinct from a **clipped lane**, which is a sweep lane cut where it
enters an exclusion. Every leg is routed; only sweep lanes are clipped.

**Blocked leg** — a leg with no route within the detour budget, or whose
destination lies inside an exclusion. A blocked leg is an abort with a reason,
never a straight line flown anyway.

**Connected free-space path** — a sequence of segments through observed
free space with the required aircraft clearance. A visible straight gap
alone is not evidence of a connected path.

**Corridor progress** — signed displacement along the corridor axis from its
entrance. Returning through the entrance is distinct from reaching its far end.

**Infeasible corridor** — a corridor whose obstacle and wall clearance bands
block every through path at the required clearance. It is distinct from a
feasible corridor that the current planner fails to traverse.

## Perception, continued

**Dwell** — the aircraft holds a heading, stationary, while the detector's
verdicts accumulate. A step of the sweep is decided on the whole dwell, never
on a single frame.

**Confident dwell** — a dwell in which most of the samples agreed. What makes
covering a full turn safe: the hazard of a long sweep was never its length, it
was acting on the first frame that said yes.

**Lettering path** — how the letters were separated from the board.
*Brightness* asks whether a pixel is brighter than the board; *stroke* asks
whether it is brighter than its immediate surroundings. A shadow changes the
first answer and not the second. Both feed the same glyph reader; either may
confirm.

## Evidence, continued

**Scan ledger** — the list of everything decoded, identified or refused during
a run, de-duplicated, with matches tagged and refusals carrying their reason.
One row per distinct observation; the repeat count is itself evidence, since it
separates a solid read from a single-frame blip.

**Stage-gated recording** — a measurement taken only while the mission reports
the state under investigation. An ungated probe of the red-zone detector caught
the aircraft on the pad and produced a confident wrong answer; the gate is what
makes a recording evidence about a stage rather than about whenever the probe
happened to look.

**Declared land-in-place** — a landing spot a focused trial records from its
own onboard pose at the moment it commands LAND, before touching down. The
independent contact grader accepts the skids settling within a radius of it,
given a gentle level touchdown and the FCU reporting LAND; everything else
stays an unexpected contact. A full mission lands at home, declares nothing
and keeps the home rule alone. Where the aircraft landed remains the mission
grader's own check, not an exemption in the contact evidence.

**Parked cargo** — where an unloaded fixture leaves the payload: on the pad,
clear of the airframe. An unloaded airframe is built without the detachable
joint that carries the payload, so cargo left at the spawn drops onto the pad
against a landing skid and records thousands of aircraft contacts before the
flight even arms.
