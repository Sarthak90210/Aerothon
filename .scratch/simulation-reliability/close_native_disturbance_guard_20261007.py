"""Close diagnostic source, runtime and audit verification after native disarm."""
import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_render_split_return_disturbance_guard_20261007'
snapshot=root/'.scratch/native_disturbance_guard_candidate_20261007'
result=json.loads((out/'trial_result.json').read_text());focused=json.loads((out/'focused_summary.json').read_text())
assert result['final_armed'] is False and result['disarm_evidence']['connected']
manifest=json.loads((out/'source_manifest.json').read_text())
for name,sha in manifest.items():
 path=Path(name) if Path(name).is_absolute() else snapshot/name
 assert hashlib.sha256(path.read_bytes()).hexdigest()==sha,name
runtime=json.loads((out/'runtime_configuration_manifest.json').read_text())
for name,sha in runtime['sha256'].items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==sha,name
for name in ('decision_inputs.json','decision_inputs_navigation.json'):
 audit=json.loads((out/name).read_text());assert audit['pass'] and not audit['missing_nodes'] and not audit['forbidden_subscriptions']
 assert {'velocity_controller_capture_driver','velocity_controller_clock_driver'} <= audit['nodes'].keys()
imports=json.loads((out/'owned_node_import_resolution_20261007.json').read_text());assert imports['all_match_frozen']
archive=json.loads((out/'candidate_archive_review_20261007.json').read_text())
assert hashlib.sha256((out/'frozen_candidate_source.zip').read_bytes()).hexdigest()==archive['archive_sha256']
review=dict(scope='Focused stationary-entry native return only; neither full rendered mission nor gust qualification',focused_result=focused,source_manifest_verified=True,runtime_archive_verified=True,helper_node_input_audits_verified=True,controller_import_resolution_verified=True,absolute_wsl_paths_verified=True,archive_sha256=archive['archive_sha256'],accepted_for_production=False,remaining_failure='Same admission guard still contacts in physical dirty0 and late1 gust/delay cases')
with (out/'closed_diagnostic_review_20261007.json').open('x') as f:json.dump(review,f,indent=2)
print(json.dumps(review,indent=2))
