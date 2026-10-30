#!/bin/bash
# The whole venue grid with the operator's course points (home, corridor ends)
# given as the GCS applies them: RTF 1, two at a time.
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"
W=logs/venue_20261030/worlds
RTF=1.0 PAR=2 FLY_EXTRA=--course-points bash .scratch/venue_20261030/driver/run_headless.sh \
  "${1:-logs/venue_20261030/headless_course}" $W/venue_c0*.json $W/venue_c1*.json
