#!/bin/bash
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"
out=${1:?evidence dir}
test ! -e "$out" || { echo 'Fresh evidence directory required'; exit 1; }
mkdir -p "$out"
set +u; source /opt/ros/jazzy/setup.bash; source "$HOME/aerothon_stack/install/setup.bash"; source install/setup.bash
export ROS_DOMAIN_ID=43 ROS_LOCALHOST_ONLY=1 GZ_PARTITION=aerothon_m2 GZ_IP=127.0.0.1
exec python3 sim/delivery_truth.py --out $out/truth.jsonl --vehicle-out $out/vehicle_truth.jsonl > $out/truth.log 2>&1
