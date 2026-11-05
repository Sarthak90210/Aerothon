"""Generate a gate-only field trial with explicit contract and source guards."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
template=Path(__file__).with_name('run_buffered_scan_navigation_seed3_20261007.py').read_text()
old="""check=root/'logs/reliability_buffered_scan_stamped_regressions_owned_20261007'
assert json.loads((check/'status.json').read_text())['state']=='COMPLETED'
assert '29 passed' in (check/'output.log').read_text()"""
new="""check=root/'logs/reliability_gate_pause_inline_contract_20261007'
contract=json.loads((check/'report.json').read_text())
assert contract['passed'] and len(contract['checks'])==5
assert contract['source_sha256']==hashlib.sha256((snapshot/'src/aerothon_mission/mission_bt/mission_bt/gate_braking_candidate.py').read_bytes()).hexdigest()"""
assert template.count(old)==1;template=template.replace(old,new)
replacements={
    '.scratch/buffered_scan_motion_candidate_20261007':'.scratch/gate_pause_motion_candidate_20261007',
    'logs/reliability_buffered_stamped_fixture_preparation_20261007/rejected_regression_source.zip':
        'logs/reliability_gate_pause_navigation_source_20261007/frozen_source.zip',
    "review=json.loads((archive_path.parent/'report.json').read_text())":
        "review=json.loads((archive_path.parent/'candidate_provenance.json').read_text())",
    "review['rejected_source_archive_verified']":"review['source_archive_verified']",
    "review['rejected_archive_sha256']":"review['source_archive_sha256']",
    'from avoidance import velocity_controller,buffered_scan_pose':'from avoidance import velocity_controller\nfrom mission_bt import gate_braking_candidate',
    '(velocity_controller,buffered_scan_pose)':'(velocity_controller,gate_braking_candidate)',
    'logs/reliability_buffered_scan_navigation_seed3_20261007':'logs/reliability_gate_pause_navigation_seed5_20261007',
    "seed=3,condition='calm'":"seed=5,condition='field'",
    "'calm',3,out,2.,1200.,226":"'field',5,out,2.,1200.,223",
    'my_world_calm_s3/source_manifest.json':'my_world_field_s5/source_manifest.json',
}
for old,new in replacements.items():
    assert old in template,old;template=template.replace(old,new)
target=Path(__file__).with_name('run_gate_pause_navigation_seed5_20261007.py')
assert not target.exists();target.write_text(template)
print(str(target))
