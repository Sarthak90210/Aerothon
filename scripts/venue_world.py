#!/usr/bin/env python3
"""The venue as the operator surveyed it (30 Oct 2026), as a world-maker world.

Positions come from the operator's GPS survey, taken about the take-off pad
(home 13.1705900, 77.5331760): both corridors' ends, the delivery zone's four
corners and the fence point behind take-off on the right. The corridors run
286.5 deg true, so the world is built in that corridor frame (forward, left)
and turned into ENU about home: the simulator's zone corners are then turned
16.5 deg off east-west, as the organisers' coordinates will be.

Sizes are the GCS preset "AeroTHON 2026 venue (30 Oct survey)", the operator's
figures where they differ from the PDF: lanes 6 x 3.5 m, walls 3 m, a 1.5-2 m
gap, two 2 m obstacles in the exit lane reaching at most 1.5 m and 4-5 cm
thick, one 3 x 3 m red zone, a 0.5 m red take-off pad with the start marker
about 1 m in front of it.

Taken from the survey, fitted: the zone, 17.8 m deep and 23.9 m wide, square
to the corridors (its corners miss that rectangle by 1.2 m at most), from 12.8
m in front of home; the corridor mouths 5.5 m in front of home (5.2-5.7 m
surveyed). Home is centred on the gap between the lanes, as the operator
describes it (the survey put it 1.6 m left of the middle). The fence point
behind on the left was typed 122 m off; it is the right one mirrored about
the take-off axis ("really wide on the back side").

    python3 scripts/venue_world.py --out sim/worlds/aerothon26_venue.json
    python3 scripts/venue_world.py --reach-m 1.0 --first-side right --target b \\
        --red mid-right --out sim/worlds/aerothon26_venue_r10.json

Refuses (exit 2) a world world_spec.validate refuses.
"""
import argparse
import copy
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src/aerothon_mission/mission_bt"))

import world_spec as W                                  # noqa: E402
from mission_bt import arena_dimensions as A            # noqa: E402

PRESET = "AeroTHON 2026 venue (30 Oct survey)"
COLOURS = {"green": "#00B140", "exit": "#0000FF", "red": "#FF0000"}
# The corridors' axis, true bearing, from both lanes' surveyed ends; as an
# ENU heading (counter-clockwise from east).
CORRIDOR_BEARING_DEG = 286.52
HEADING_DEG = 90.0 - CORRIDOR_BEARING_DEG + 360.0          # 163.48
MOUTH_M = 5.5                       # corridor mouths in front of home
ZONE_CENTRE = (21.71, 0.93)         # corridor frame (forward, left)
ZONE_DEPTH_M, ZONE_WIDTH_M = 17.8, 23.9
BEHIND = (-5.42, 23.36)             # back-right surveyed; back-left mirrored
# Pads (zone frame: forward, left of the zone centre) and red-zone places.
PAD_LAYOUTS = {
    "spread": {"a": (-5.5, 8.0), "b": (5.0, 8.5), "c": (-4.0, -3.0),
               "d": (0.5, -8.5), "e": (5.0, -1.0)},
    "far": {"a": (-5.0, -8.0), "b": (5.0, -8.0), "c": (5.5, 7.5),
            "d": (0.0, -7.5), "e": (-5.5, 7.0)},
}
RED_PLACES = {"mid-left": (0.0, 3.5), "before-exit": (-5.0, 2.0),
              "mid-right": (3.5, -4.5), "centre": (0.5, -1.5)}


def to_world(fwd, left):
    """Corridor frame (forward, left of the take-off axis) -> world ENU about home."""
    h = math.radians(HEADING_DEG)
    return (round(fwd * math.cos(h) - left * math.sin(h), 4),
            round(fwd * math.sin(h) + left * math.cos(h), 4))


def zone_point(a, b):
    return to_world(ZONE_CENTRE[0] + a, ZONE_CENTRE[1] + b)


def build(name, target="c", reach_m=1.5, first_side="left", gap_m=2.0,
          marker_ahead_m=1.5, pads="spread", red="mid-left", board_u=(2.0, 4.0)):
    dims = copy.deepcopy(A.BUILTIN_PRESETS[PRESET])
    width = dims["corridor"]["width_m"]
    dims["corridor"]["spacing_m"] = width + float(gap_m)
    dims["obstacle"]["reach_frac"] = round(float(reach_m) / width, 4)
    d = A.validate(dims)
    half = d["corridor"]["spacing_m"] / 2.0
    gx, gy = to_world(MOUTH_M, half)
    # Exit-lane boards from its zone-side entrance; v > 0 is the left wall
    # flying home. apply_dimensions sizes them (reach, 2 m) and keeps the wall.
    side = 1.0 if first_side == "left" else -1.0
    boards = [{"u": float(u), "v": side * (1 if i % 2 == 0 else -1), "w": 0.045,
               "d": 1.0, "h": 2.0, "yaw_deg": 0.0} for i, u in enumerate(board_u)]
    zx, zy = zone_point(0.0, 0.0)
    spec = {
        "schema": W.SCHEMA,
        "name": name,
        "takeoff": {"x": 0.0, "y": 0.0, "yaw_deg": round(HEADING_DEG, 3),
                    "pad_m": 0.5, "pad_colour": "#FF0000",
                    "start_marker_ahead_m": float(marker_ahead_m)},
        "corridor": {"x": gx, "y": gy, "yaw_deg": round(HEADING_DEG, 3)},
        "return_corridor": {"linked": True, "obstacles": boards},
        "delivery_zone": {"x": zx, "y": zy, "w": ZONE_DEPTH_M, "h": ZONE_WIDTH_M,
                          "yaw_deg": round(HEADING_DEG, 3)},
        "geofence": {"mode": "behind",
                     "behind": [list(to_world(BEHIND[0], BEHIND[1])),
                                list(to_world(BEHIND[0], -BEHIND[1]))]},
        "red_zones": [{"x": zone_point(*RED_PLACES[red])[0],
                       "y": zone_point(*RED_PLACES[red])[1],
                       "w": 3.0, "h": 3.0, "yaw_deg": round(HEADING_DEG, 3)}],
        "pads": {k: {"x": zone_point(*ab)[0], "y": zone_point(*ab)[1],
                     "yaw_deg": round(HEADING_DEG, 3)}
                 for k, ab in PAD_LAYOUTS[pads].items()},
        "decoys": [],
        "start_target": target,
        "qr": {"kind": "apriltag_36h11",
               "ids": {"a": 100, "b": 200, "c": 300, "d": 400, "e": 500}},
        "banner": {"colours": dict(COLOURS)},
        "conditions": {"preset": "calm"},
    }
    return W.apply_dimensions(spec, d)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--target", default="c", help="pad the start marker names: a-e")
    ap.add_argument("--reach-m", type=float, default=1.5,
                    help="how far each exit-lane board reaches from its wall")
    ap.add_argument("--first-side", choices=("left", "right"), default="left",
                    help="wall of the first board, flying home")
    ap.add_argument("--board-u", default="2.0,4.0",
                    help="boards' distances from the exit lane's zone-side entrance")
    ap.add_argument("--gap-m", type=float, default=2.0, help="between the two lanes")
    ap.add_argument("--marker-ahead-m", type=float, default=1.5,
                    help="start marker centre in front of the pad centre")
    ap.add_argument("--pads", choices=sorted(PAD_LAYOUTS), default="spread")
    ap.add_argument("--red", choices=sorted(RED_PLACES), default="mid-left")
    a = ap.parse_args(argv)
    spec = build(a.out.stem, a.target.lower(), a.reach_m, a.first_side, a.gap_m,
                 a.marker_ahead_m, a.pads, a.red,
                 tuple(float(v) for v in a.board_u.split(",")))
    errs, warns = W.validate(spec)
    for w in warns:
        print("warning:", w)
    if errs:
        print("REFUSED:\n  " + "\n  ".join(errs))
        return 2
    a.out.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print("wrote", a.out, "corridor alt", round(W.corridor_alt(spec), 3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
