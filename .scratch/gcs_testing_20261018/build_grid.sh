#!/usr/bin/env bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
set +u; source /opt/ros/jazzy/setup.bash; set -u
colcon build --symlink-install --packages-select aerothon_slam_grid 2>&1 | tail -5
