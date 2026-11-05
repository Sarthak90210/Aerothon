#!/usr/bin/env bash
# Repeat the focused native return on V40, into a NEW output directory.
# The V39 failure at logs/reliability_reduced_v39_focused_split_s20261003_20261009
# is preserved untouched; nothing here reads or writes it.
set -eo pipefail
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1
export AEROTHON_ACCEPTANCE_DOMAIN=30 ROS_DOMAIN_ID=30 ROS_LOCALHOST_ONLY=1
export AEROTHON_RENDER_TRIAL=return-corridor
export AEROTHON_CORRIDOR_ENTRY="$PWD/.scratch/simulation-reliability/return_entry_split_v38_s20261003_20261009.json"
export AEROTHON_CORRIDOR_HANDOVER=moving
unset AEROTHON_MOTION_FORECAST_OUT
python3 - <<'PY'
import hashlib,json
from pathlib import Path
manifest=json.loads(Path('.scratch/reduced_scope_v40_candidate_20261010/source_manifest.json').read_text())
assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
PY
out="$PWD/logs/reliability_reduced_v40_focused_split_s20261003_20261010"
status=0
bash scripts/run_recorded_acceptance.sh sim/worlds/split_corridors.json 20261003 "$out" "$PWD/logs/delivery_profile_20261005.json" || status=$?
# Full mission grading intentionally fails for an operator-only return replay.
python3 .scratch/simulation-reliability/grade_focused_return.py "$out"
python3 - "$out" <<'PY'
import hashlib,json,re,sys
from pathlib import Path
root=Path.cwd();out=Path(sys.argv[1])
focused=json.loads((out/'focused_summary.json').read_text())
grade=json.loads((out/'grade.json').read_text())
contacts=grade['aircraft_contact_evidence']
assert focused['focused_pass'] and contacts['valid'] and contacts['contact_free'] and contacts['ground_canary']
assert contacts['channels']==7 and contacts['unexpected_contacts']==[]
# The landing the trial declared from its own FCU pose, before touching down,
# and the skids actually settling on it.
contract=json.loads((out/'landing_contract.json').read_text())
assert contract['frame']=='home_local_enu' and contract['anchor'] is not None
assert contract['radius_m']==1.5 and 'failure' not in contract
assert contacts['declared_landing_pairs']>0
# The unloaded scene must carry no cargo on the airframe at all.
world=(out/'flight_world.sdf').read_text()
i=world.index('<model name="aerothon_payload">');a=world.index('<pose>',i)
payload=[float(v) for v in world[a+6:world.index('</pose>',a)].split()[:3]]
j=world.index('<name>aerothon_iris</name>');b=world.index('<pose>',j)
spawn=[float(v) for v in world[b+6:world.index('</pose>',b)].split()[:3]]
separation=round(sum((payload[k]-spawn[k])**2 for k in (0,1))**.5,3)
assert separation>=1.,separation
assert 'DetachableJoint' not in (out/'flight_vehicle.sdf').read_text()
manifest=json.loads(Path('.scratch/reduced_scope_v40_candidate_20261010/source_manifest.json').read_text())
recorded=json.loads((out/'source_manifest.json').read_text())
assert all(recorded[name]==sha and hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
cfg=json.loads((out/'configuration.json').read_text())
assert cfg['handover_mode']=='moving' and cfg['payload_fixture']=='unloaded'
assert cfg['handover_driver_sha256']==manifest['sim/corridor_trial.py']
review=dict(focused_return_pass=True,source_unchanged=True,source_files=len(manifest),version='V40',
 source_archive_sha256=json.loads(Path('logs/reliability_reduced_scope_v40_source_20261010/provenance.json').read_text())['archive_sha256'],
 focused=focused,aircraft_contact_evidence=contacts,configuration=cfg,
 declared_landing_contract=contract,
 unloaded_scene=dict(payload_pose=payload,spawn_pose=spawn,separation_m=separation,
   detachable_joint=False,
   note='the unloaded fixture parks the cargo clear of the airframe instead of '
        'dropping it onto the pad against a landing skid'),
 preserved_v39_failure='logs/reliability_reduced_v39_focused_split_s20261003_20261009',
 full_mission_qualified=False,
 files={str(p.relative_to(out)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in out.rglob('*') if p.is_file()})
with (out/'focused_source_closed_review.json').open('x') as stream:json.dump(review,stream,indent=2)
print(json.dumps(dict(focused_return_pass=True,minimum_clearance_m=focused['measured_corridor_clearance_m'],
 declared_landing_pairs=contacts['declared_landing_pairs'],unexpected_contacts=0,
 payload_separation_m=separation,source_files=len(manifest))))
PY
