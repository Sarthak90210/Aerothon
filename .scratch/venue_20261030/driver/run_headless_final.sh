#!/bin/bash
# Headless runs on the merged source (course points + exit hold), RTF 1, two
# at a time: the three red-past-the-exit worlds without course points (the
# exit hold), then the whole grid with course points (--course-points).
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"
S=.scratch/venue_20261030/driver
W=logs/venue_20261030/worlds
RTF=1.0 PAR=2 bash $S/run_headless.sh logs/venue_20261030/headless_final_nocourse \
  $W/venue_c04_r125_g20_right.json $W/venue_c07_r15_g15_left.json $W/venue_c09_r10_g15_left.json
RTF=1.0 PAR=2 FLY_EXTRA=--course-points bash $S/run_headless.sh logs/venue_20261030/headless_final_course \
  $W/venue_c0*.json $W/venue_c1*.json
