#!/bin/bash
# Resume the headless grid after the operator's pause: cases 3-11, RTF 1, two at a time.
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"
W=logs/venue_20261030/worlds
RTF=1.0 PAR=2 bash .scratch/venue_20261030/driver/run_headless.sh "$1" \
  $W/venue_c03_r125_g20_left.json $W/venue_c04_r125_g20_right.json $W/venue_c05_r15_g20_left.json \
  $W/venue_c06_r15_g20_right.json $W/venue_c07_r15_g15_left.json $W/venue_c08_r15_g15_right.json \
  $W/venue_c09_r10_g15_left.json $W/venue_c10_r125_g15_right.json $W/venue_c11_marker100.json
