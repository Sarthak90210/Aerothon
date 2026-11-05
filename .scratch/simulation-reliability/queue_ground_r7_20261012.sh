#!/usr/bin/env bash
# Wait, inside WSL, for the r6 batch runner to exit, then fly ground-only (r7).
while pgrep -f '[r]un_banner_placements_rendered_r6' >/dev/null; do sleep 30; done
exec bash "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/simulation-reliability/run_banner_ground_rendered_r7_20261012.sh"
