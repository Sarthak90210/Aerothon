#!/usr/bin/env python3
"""The organisers' Track 1 field (PDF, 23 Oct 2026) as a world-maker world.

Sizes come from the GCS preset "AeroTHON 2026 Track 1 field (organiser PDF)"
through world_spec.apply_dimensions, exactly as the world editor builds them;
positions follow the PDF's Mission 2 drawing (page 9), which the organisers
say may change on the day: take-off zone with the start QR on the left, the
entry corridor (green boards) above the exit corridor (blue boards, three
6 ft boards inside), both opening straight into the 40 x 30 m delivery zone,
five 1 m QR pads and one 10 ft red zone in it.

    python3 scripts/field_pdf_world.py --target c --out sim/worlds/aerothon26_field.json
    python3 scripts/field_pdf_world.py --length-m 10 --target a \
        --out sim/worlds/aerothon26_field_L10.json     # the drawing's 10 m lanes

Refuses (exit 2) a world world_spec.validate refuses.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src/aerothon_mission/mission_bt"))

import world_spec as W                                  # noqa: E402
from mission_bt import arena_dimensions as A            # noqa: E402

PRESET = "AeroTHON 2026 Track 1 field (organiser PDF)"
# The field PDF's shades: entry #00B140, exit #0000FF, red zone #FF0000.
COLOURS = {"green": "#00B140", "exit": "#0000FF", "red": "#FF0000"}


def build(name, target, length_m=None, spacing_m=None):
    dims = copy.deepcopy(A.BUILTIN_PRESETS[PRESET])
    if length_m:
        dims["corridor"]["length_m"] = float(length_m)
    if spacing_m:
        dims["corridor"]["spacing_m"] = float(spacing_m)
    d = A.validate(dims)
    L = d["corridor"]["length_m"]
    gate_x = 2.0
    zone_x0 = gate_x + L + 0.3            # the lanes open straight into the zone
    spec = {
        "schema": W.SCHEMA,
        "name": name,
        "takeoff": {"x": -4.0, "y": 0.0, "yaw_deg": 0.0},
        # Entry corridor above (port of) the exit corridor, as drawn.
        "corridor": {"x": gate_x, "y": d["corridor"]["spacing_m"] / 2.0, "yaw_deg": 0.0},
        "return_corridor": {
            "linked": True,
            # Three boards, alternating walls, in the lane frame from the
            # exit corridor's zone-side entrance; apply_dimensions sizes them
            # (3.5 ft across, 6 ft tall) and keeps each one's wall.
            "obstacles": [{"u": round(f * L, 3), "v": side, "w": 0.10, "d": 1.0,
                           "h": 1.8, "yaw_deg": 0.0}
                          for f, side in ((0.25, 1.0), (0.5, -1.0), (0.75, 1.0))],
        },
        "delivery_zone": {"x": zone_x0 + 20.0, "y": 0.0, "w": 40.0, "h": 30.0},
        "geofence": {"mode": "auto", "margin": 4.0},
        "red_zones": [{"x": zone_x0 + 27.0, "y": 4.0, "w": 3.0, "h": 3.0, "yaw_deg": 0.0}],
        "pads": {"a": {"x": zone_x0 + 5.0, "y": 11.0},
                 "b": {"x": zone_x0 + 36.0, "y": 11.0},
                 "c": {"x": zone_x0 + 10.0, "y": -2.0},
                 "d": {"x": zone_x0 + 19.0, "y": -11.0},
                 "e": {"x": zone_x0 + 31.0, "y": -5.0}},
        "decoys": [],
        "start_target": target,
        "banner": {"colours": dict(COLOURS)},
        "conditions": {"preset": "calm"},
    }
    return W.apply_dimensions(spec, d)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--target", default="c", help="pad the start QR names: a-e")
    ap.add_argument("--length-m", type=float, help="corridor length (PDF walls: 22 ft)")
    ap.add_argument("--spacing-m", type=float, help="lane spacing, centre to centre")
    a = ap.parse_args(argv)
    spec = build(a.out.stem, a.target.lower(), a.length_m, a.spacing_m)
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
