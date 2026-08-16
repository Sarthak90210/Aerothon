#!/usr/bin/env python3
"""Resolve runtime asset URIs in the competition SDF.

Gazebo is deliberately started by the master shell instead of as a child of
ROS launch. On the target workstation this avoids a Gazebo transport startup
stall and lets the launcher gate vehicle spawning on /gazebo/worlds.
"""

from argparse import ArgumentParser
from pathlib import Path
import json
import shutil
import tempfile


WHITE = "<material><ambient>1 1 1 1</ambient><diffuse>1 1 1 1</diffuse></material>"
BLACK = "<material><ambient>0.002 0.002 0.002 1</ambient><diffuse>0.002 0.002 0.002 1</diffuse></material>"
GREEN = "<material><ambient>0.01 0.48 0.18 1</ambient><diffuse>0.01 0.62 0.24 1</diffuse></material>"

# Compact 5x7 block font used for signs. Geometry, unlike synchronized PBR
# textures, renders reliably in both the Gazebo GUI and simulated camera.
FONT = {
    "A": ["01110","10001","10001","11111","10001","10001","10001"],
    "B": ["11110","10001","10001","11110","10001","10001","11110"],
    "D": ["11110","10001","10001","10001","10001","10001","11110"],
    "E": ["11111","10000","10000","11110","10000","10000","11111"],
    "H": ["10001","10001","10001","11111","10001","10001","10001"],
    "N": ["10001","11001","11001","10101","10011","10011","10001"],
    "O": ["01110","10001","10001","10001","10001","10001","01110"],
    "R": ["11110","10001","10001","11110","10100","10010","10001"],
    "T": ["11111","00100","00100","00100","00100","00100","00100"],
    "Z": ["11111","00001","00010","00100","01000","10000","11111"],
    "0": ["01110","10001","10011","10101","11001","10001","01110"],
    "2": ["01110","10001","00001","00010","00100","01000","11111"],
    "6": ["00110","01000","10000","11110","10001","10001","01110"],
    " ": ["00000"] * 7,
}


def box_visual(name: str, pose: str, size: str, material: str) -> str:
    if len(pose.split()) == 3:
        pose = f"{pose} 0 0 0"
    return (f'<visual name="{name}"><pose>{pose}</pose><geometry><box><size>{size}'
            f'</size></box></geometry>{material}</visual>')


def qr_visuals(matrix: list[list[bool]], size: float, prefix: str) -> str:
    """White plate plus horizontally merged black QR module runs."""
    n = len(matrix)
    cell = size / n
    visuals = [box_visual(f"{prefix}_white_plate", "0 0 0", f"{size} {size} 0.04", WHITE)]
    idx = 0
    for row, modules in enumerate(matrix):
        col = 0
        while col < n:
            if not modules[col]:
                col += 1
                continue
            start = col
            while col < n and modules[col]:
                col += 1
            run = col - start
            x = -size / 2 + (start + run / 2) * cell
            y = size / 2 - (row + 0.5) * cell
            visuals.append(box_visual(
                f"{prefix}_black_{idx}", f"{x:.6f} {y:.6f} 0.026",
                f"{run * cell:.6f} {cell:.6f} 0.012", BLACK))
            idx += 1
    return "\n".join(visuals)


def bitmap_runs(text: str):
    rows = ["" for _ in range(7)]
    for char in text.upper():
        glyph = FONT[char]
        for row in range(7):
            rows[row] += glyph[row] + "0"
    return rows


def banner_visuals() -> str:
    text = "AEROTHON"
    rows = bitmap_runs(text)
    cols = len(rows[0])
    cell_y, cell_z = 3.25 / cols, 0.115
    center_z = 3.38
    visuals = [
        box_visual("banner_board", f"0 0 {center_z}", "0.12 3.7 1.15", GREEN),
    ]
    # Raised white frame on both faces.
    for face, x in (("front", -0.071), ("back", 0.071)):
        visuals.extend([
            box_visual(f"banner_{face}_frame_top", f"{x} 0 {center_z + 0.50}", "0.022 3.48 0.07", WHITE),
            box_visual(f"banner_{face}_frame_bottom", f"{x} 0 {center_z - 0.50}", "0.022 3.48 0.07", WHITE),
            box_visual(f"banner_{face}_frame_left", f"{x} 1.705 {center_z}", "0.022 0.07 1.07", WHITE),
            box_visual(f"banner_{face}_frame_right", f"{x} -1.705 {center_z}", "0.022 0.07 1.07", WHITE),
        ])
    idx = 0
    for face, x, mirror in (("front", -0.071, False), ("back", 0.071, True)):
        for row, bits in enumerate(rows):
            source = bits[::-1] if mirror else bits
            col = 0
            while col < cols:
                if source[col] != "1":
                    col += 1
                    continue
                start = col
                while col < cols and source[col] == "1":
                    col += 1
                run = col - start
                y = 1.625 - (start + run / 2) * cell_y
                z = center_z + (3 - row) * cell_z
                visuals.append(box_visual(
                    f"banner_{face}_{idx}", f"{x:.3f} {y:.6f} {z:.6f}",
                    f"0.022 {run * cell_y:.6f} {cell_z:.6f}", WHITE))
                idx += 1
    return "\n".join(visuals)


def red_zone_visuals(width: float, height: float, prefix: str) -> str:
    """Raised white border and RED ZONE block text over the existing red base."""
    t = min(width, height) * 0.055
    z = 0.066
    visuals = [
        box_visual(f"{prefix}_border_n", f"0 {height/2-t/2:.4f} {z}", f"{width} {t} 0.022", WHITE),
        box_visual(f"{prefix}_border_s", f"0 {-height/2+t/2:.4f} {z}", f"{width} {t} 0.022", WHITE),
        box_visual(f"{prefix}_border_e", f"{width/2-t/2:.4f} 0 {z}", f"{t} {height} 0.022", WHITE),
        box_visual(f"{prefix}_border_w", f"{-width/2+t/2:.4f} 0 {z}", f"{t} {height} 0.022", WHITE),
    ]
    rows = bitmap_runs("RED ZONE")
    cols = len(rows[0])
    cell_x = width * 0.68 / cols
    cell_y = min(height * 0.09, cell_x * 1.35)
    idx = 0
    for row, bits in enumerate(rows):
        col = 0
        while col < cols:
            if bits[col] != "1":
                col += 1
                continue
            start = col
            while col < cols and bits[col] == "1":
                col += 1
            run = col - start
            x = -width * 0.34 + (start + run / 2) * cell_x
            y = (3 - row) * cell_y
            visuals.append(box_visual(
                f"{prefix}_text_{idx}", f"{x:.6f} {y:.6f} {z}",
                f"{run * cell_x:.6f} {cell_y:.6f} 0.022", WHITE))
            idx += 1
    return "\n".join(visuals)


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    # Ogre cannot resolve file:// URIs whose path contains spaces, even when
    # percent-encoded. Mirror the small generated texture set into /tmp.
    runtime_assets = Path(tempfile.gettempdir()) / "aerothon_m2_assets"
    runtime_assets.mkdir(parents=True, exist_ok=True)
    for asset in args.assets.iterdir():
        if asset.is_file():
            shutil.copy2(asset, runtime_assets / asset.name)

    world = args.source.read_text(encoding="utf-8")
    matrices_path = args.assets / "qr_matrices.json"
    if not matrices_path.exists():
        raise SystemExit(f"Missing {matrices_path}; run generate_competition_assets.py")
    matrices = json.loads(matrices_path.read_text(encoding="utf-8"))
    replacements = {
        "@QR_START_VISUALS@": qr_visuals(matrices["qr_start.png"], 2.2, "start_qr"),
        "@QR_TARGET_A_VISUALS@": qr_visuals(matrices["qr_target_a.png"], 3.0, "target_a"),
        "@QR_TARGET_B_VISUALS@": qr_visuals(matrices["qr_target_b.png"], 3.0, "target_b"),
        "@QR_TARGET_C_VISUALS@": qr_visuals(matrices["qr_target_c.png"], 3.0, "target_c"),
        "@QR_TARGET_D_VISUALS@": qr_visuals(matrices["qr_target_d.png"], 3.0, "target_d"),
        "@QR_TARGET_E_VISUALS@": qr_visuals(matrices["qr_target_e.png"], 3.0, "target_e"),
        "@AEROTHON_BANNER_VISUALS@": banner_visuals(),
        "@RED_ZONE_MAIN_VISUALS@": red_zone_visuals(10.0, 7.0, "red_main"),
        "@RED_ZONE_NW_VISUALS@": red_zone_visuals(6.0, 4.0, "red_nw"),
        "@RED_ZONE_SOUTH_VISUALS@": red_zone_visuals(7.0, 4.0, "red_south"),
    }
    for token, geometry in replacements.items():
        if token not in world:
            raise SystemExit(f"World is missing geometry token {token}")
        world = world.replace(token, geometry)
    world = world.replace("@SIM_GAZEBO_ASSET_URI@", runtime_assets.as_uri())
    args.output.write_text(world, encoding="utf-8")


if __name__ == "__main__":
    main()
