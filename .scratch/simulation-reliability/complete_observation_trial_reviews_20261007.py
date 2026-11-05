"""Preserve review corrections and verify the gate-only closed trial."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_buffered_scan_navigation_field2_20261007'
path=out/'closed_trial_review.json';old=path.read_bytes()
(out/'sampled_clearance_only_review_original.json').write_bytes(old)
review=json.loads(old)
review['sampled_clearance_meets_reserve']=review['sampling_reserve_pass']
review['sampling_reserve_pass']=False
review['qualification_note']='Return corridor was never traversed; sampled clearance cannot qualify the original return-clearance failure'
path.write_text(json.dumps(review,indent=2)+'\n')
template=Path(__file__).with_name('close_buffered_navigation_review_20261007.py').read_text()
template=template.replace('logs/reliability_buffered_stamped_fixture_preparation_20261007/rejected_regression_source.zip',
    'logs/reliability_gate_pause_navigation_source_20261007/frozen_source.zip')
template=template.replace('.scratch/buffered_scan_motion_candidate_20261007','.scratch/gate_pause_motion_candidate_20261007')
target=Path(__file__).with_name('close_gate_pause_navigation_review_20261007.py')
assert not target.exists();target.write_text(template)
print('Preserved sampled-only review and prepared gate-only closure verifier')
