#!/usr/bin/env bash
# Wait inside WSL for the p2r2 batch, then re-fly ground-only (p2r3).
while pgrep -f '[r]un_phase2_rendered_p2r2' >/dev/null; do sleep 30; done
exec bash "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/simulation-reliability/run_phase2_rendered_p2r3_20261012.sh"
