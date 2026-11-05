#!/usr/bin/env bash
set -eo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
ffmpeg -v error -i logs/reliability_reduced_v16_render_split_corridors_s20261003_20261008/onboard.avi -vf 'select=eq(n\,640)' -frames:v 1 .scratch/simulation-reliability/v16_split_search_frame640_20261008.png