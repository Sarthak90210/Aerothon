#!/bin/bash
# The rendered (Gazebo window) venue runs on the final source (8ecc16d, dwell waits for frames), one after
# another, organiser inputs entered through the GCS:
#   1. aerothon26_venue, target C: six fence points typed, home RECORDED with
#      the simulated aircraft's GPS, corridor ends typed (course points)
#   2. aerothon26_venue_r10, target D: the six fence points only
#   3. aerothon26_venue_far, target B: course points; red square past the exit
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"
S=.scratch/venue_20261030/driver
D=logs/venue_20261030
VENUE_COURSE=1 VENUE_RECORD_HOME=1 bash $S/run_venue.sh aerothon26_venue $D/gui_s2_r1_venue_course c
VENUE_COURSE=0 bash $S/run_venue.sh aerothon26_venue_r10 $D/gui_s2_r2_r10_fence_only d
VENUE_COURSE=1 VENUE_RECORD_HOME=1 bash $S/run_venue.sh aerothon26_venue_far $D/gui_s2_r3_far_course b
echo "$(date -Is) gui batch done"
