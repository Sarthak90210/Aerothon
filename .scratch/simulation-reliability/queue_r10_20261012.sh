#!/usr/bin/env bash
# Wait inside WSL for the r9 batch, then fly ground and both with the laid
# sheet in front of the mouth (r10).
while pgrep -f '[r]un_banner_ground_rendered_r9' >/dev/null; do sleep 30; done
exec bash "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/simulation-reliability/run_banner_placements_rendered_r10_20261012.sh"
