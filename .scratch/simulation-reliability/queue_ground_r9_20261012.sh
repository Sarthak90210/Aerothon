#!/usr/bin/env bash
# Wait inside WSL for the r8 batch runner, then fly ground-only (r9).
while pgrep -f '[r]un_banner_placements_rendered_r8' >/dev/null; do sleep 30; done
exec bash "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/simulation-reliability/run_banner_ground_rendered_r9_20261012.sh"
