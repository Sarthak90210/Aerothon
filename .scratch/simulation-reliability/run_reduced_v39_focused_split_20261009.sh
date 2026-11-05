#!/usr/bin/env bash
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
manifest=json.loads(Path('.scratch/reduced_scope_v39_candidate_20261008/source_manifest.json').read_text())
assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
PY
out="$PWD/logs/reliability_reduced_v39_focused_split_s20261003_20261009"
status=0
bash scripts/run_recorded_acceptance.sh sim/worlds/split_corridors.json 20261003 "$out" "$PWD/logs/delivery_profile_20261005.json" || status=$?
# Full mission grading intentionally fails for an operator-only return replay.
python3 .scratch/simulation-reliability/grade_focused_return.py "$out"
python3 - "$out" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path.cwd();out=Path(sys.argv[1])
focused=json.loads((out/'focused_summary.json').read_text())
grade=json.loads((out/'grade.json').read_text())
contacts=grade['aircraft_contact_evidence']
assert focused['focused_pass'] and contacts['valid'] and contacts['contact_free'] and contacts['ground_canary']
assert contacts['channels']==7 and contacts['unexpected_contacts']==[]
manifest=json.loads(Path('.scratch/reduced_scope_v39_candidate_20261008/source_manifest.json').read_text())
recorded=json.loads((out/'source_manifest.json').read_text())
assert all(recorded[name]==sha and hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
cfg=json.loads((out/'configuration.json').read_text())
assert cfg['handover_mode']=='moving' and cfg['payload_fixture']=='unloaded'
review=dict(focused_return_pass=True,source_unchanged=True,source_files=len(manifest),
 source_archive_sha256=json.loads(Path('logs/reliability_reduced_scope_v39_source_20261008/provenance.json').read_text())['archive_sha256'],
 focused=focused,aircraft_contact_evidence=contacts,configuration=cfg,full_mission_qualified=False,
 files={str(p.relative_to(out)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in out.rglob('*') if p.is_file()})
with (out/'focused_source_closed_review.json').open('x') as stream:json.dump(review,stream,indent=2)
print(json.dumps(dict(focused_return_pass=True,minimum_clearance_m=focused['measured_corridor_clearance_m'],source_files=len(manifest))))
PY
