#!/usr/bin/env python3
"""The simulator's field markers: AprilTag 36h11 cell grids for the IDs
photographed on the venue's boards (29 Oct 2026), from OpenCV's own
dictionary so the printed tag and the detector cannot disagree.

    python3 scripts/generate_tag_matrices.py      # needs cv2.aruco

Writes src/aerothon_sim/sim_gazebo/materials/tag36h11_matrices.json:
{"<id>": rows of booleans, True black, the tag's black border included}.
scripts/materialize_world.py prints these on a white board.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/aerothon_perception/perception_qr"))

from perception_qr import tag_decode              # noqa: E402

FIELD_IDS = (100, 200, 300, 400, 500)
OUT = ROOT / "src/aerothon_sim/sim_gazebo/materials/tag36h11_matrices.json"


def main():
    cells = {str(i): tag_decode.marker_cells(tag_decode.DEFAULT_DICTIONARY, i)
             for i in FIELD_IDS}
    OUT.write_text(json.dumps(cells, separators=(",", ":")) + "\n", encoding="utf-8")
    print("wrote", OUT, sorted(cells, key=int))


if __name__ == "__main__":
    main()
