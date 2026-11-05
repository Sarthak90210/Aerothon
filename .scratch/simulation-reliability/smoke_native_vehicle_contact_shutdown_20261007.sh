#!/usr/bin/env bash
set -eo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1
export ROS_DOMAIN_ID=218 ROS_LOCALHOST_ONLY=1 GZ_PARTITION=aerothon_m2 GZ_IP=127.0.0.1
export AEROTHON_WORLD_SPEC="$PWD/sim/worlds/split_corridors.json"
export AEROTHON_CONDITIONS=calm AEROTHON_CONDITIONS_SEED=20261003 AEROTHON_SEED=20261003
export AEROTHON_HEADLESS=1 AEROTHON_OPEN_GCS=0 AEROTHON_NO_REAP=1
export AEROTHON_AIRFRAME=cad AEROTHON_PAYLOAD_FIXTURE=loaded
export AEROTHON_DELIVERY_CALIBRATION="$PWD/logs/delivery_profile_20261005.json"
unset AEROTHON_RANDOM_ARENA AEROTHON_START_TARGET AEROTHON_DELIVERY_ZONE AEROTHON_GEOFENCE
out="$PWD/logs/reliability_native_vehicle_contact_shutdown_20261007"
[[ ! -e "$out" ]] || exit 2
if pgrep -f '[g]z sim|[a]rducopter|[l]aunch_level6_sim' >/dev/null; then echo 'Native simulator already active'; exit 2; fi
mkdir "$out"
python3 - "$out" <<'PY'
import sys,json
from pathlib import Path
sys.path.insert(0,'sim')
from campaign_record import source_manifest
(Path(sys.argv[1])/'source_manifest.json').write_text(json.dumps(source_manifest(Path.cwd()),indent=2))
PY
stack_pid='' contact_pid=''
cleanup() {
 [[ -z "$contact_pid" ]] || kill -INT "$contact_pid" 2>/dev/null || true
 [[ -z "$contact_pid" ]] || wait "$contact_pid" 2>/dev/null || true
 [[ -z "$stack_pid" ]] || kill -TERM -- "-$stack_pid" 2>/dev/null || true
 [[ -z "$stack_pid" ]] || wait "$stack_pid" 2>/dev/null || true
 [[ -z "$stack_pid" ]] || kill -KILL -- "-$stack_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
setsid bash scripts/launch_level6_sim.sh > "$out/stack.log" 2>&1 & stack_pid=$!
python3 sim/wait_ready.py --timeout 240 --min-pose-hz 1 --require-scan > "$out/readiness.log" 2>&1
cp /tmp/aerothon_vehicle_models/aerothon_iris_c1_webcam/model.sdf "$out/flight_vehicle.sdf"
cp /tmp/aerothon_vehicle_models/aerothon_iris_c1_webcam/vehicle_contact_sensors.json "$out/sensor_channels.json"
python3 -u sim/record_vehicle_contacts.py --model "$out/flight_vehicle.sdf" --out "$out/vehicle_contacts.jsonl" --ready "$out/contact_ready.json" --until-file "$out/stop" --timeout 45 > "$out/contact_recorder.log" 2>&1 & contact_pid=$!
wait "$contact_pid"; contact_pid=''
python3 - "$out" <<'PY'
import sys,json
from pathlib import Path
sys.path.insert(0,'sim')
from campaign_record import source_manifest
out=Path(sys.argv[1]);rows=[json.loads(s) for s in (out/'vehicle_contacts.jsonl').read_text().splitlines()]
heartbeats=[r for r in rows if r['kind']=='heartbeat'];contacts=[r for r in rows if r['kind']=='contacts' and r['contacts']]
review=dict(scope='Unarmed normal-startup native contact liveness only; no mission acceptance',source_unchanged=json.loads((out/'source_manifest.json').read_text())==source_manifest(Path.cwd()),ready=(out/'contact_ready.json').exists(),heartbeats=len(heartbeats),all_channels_advertised=bool(heartbeats) and all(len(r['channels'])==len(r['advertised_topics']) for r in heartbeats),contact_rows=len(contacts),contact_pairs=[c for r in contacts[:5] for c in r['contacts']])
(out/'smoke_review.json').write_text(json.dumps(review,indent=2))
print(json.dumps(review,indent=2))
assert review['source_unchanged'] and review['ready'] and review['all_channels_advertised'] and contacts
PY
