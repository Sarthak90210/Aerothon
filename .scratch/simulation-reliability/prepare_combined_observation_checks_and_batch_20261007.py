"""Generate guarded checks and three preserved-failure trials without modifying source."""
from pathlib import Path
here=Path(__file__).parent
def write(name,text):
    target=here/name;assert not target.exists();target.write_text(text)
text=(here/'check_buffered_scan_stamped_regressions_20261007.py').read_text()
text=text.replace('.scratch/buffered_scan_motion_candidate_20261007','.scratch/combined_observation_motion_candidate_20261007')
write('check_combined_observation_regressions_20261007.py',text)
text=(here/'check_gate_observation_pause_20261007.py').read_text()
text=text.replace("str(root/'src/aerothon_mission/mission_bt')","str(root/'.scratch/combined_observation_motion_candidate_20261007/src/aerothon_mission/mission_bt')")
text=text.replace('reliability_gate_observation_pause_contract_20261007','reliability_combined_gate_pause_contract_20261007')
text=text.replace('from gate_observation_pause_candidate_20261007 import ObservationPausedGateAdvance','from mission_bt.gate_braking_candidate import BrakedGateAdvance as ObservationPausedGateAdvance')
text=text.replace("module=Path(__file__).with_name('gate_observation_pause_candidate_20261007.py')","module=root/'.scratch/combined_observation_motion_candidate_20261007/src/aerothon_mission/mission_bt/mission_bt/gate_braking_candidate.py'")
write('check_combined_gate_pause_20261007.py',text)
text=(here/'run_paired_scan_batch_verified_20261007.py').read_text()
text=text.replace('.scratch/paired_scan_motion_candidate_20261007','.scratch/combined_observation_motion_candidate_20261007')
text=text.replace('logs/reliability_paired_scan_navigation_s5_assets_20261007','logs/reliability_combined_observation_navigation_source_20261007')
text=text.replace('logs/reliability_focused_paired_scan_navigation_verified_20261007','logs/reliability_combined_observation_focused_navigation_20261007')
text=text.replace("qualified/'source_archive_review.json'","qualified/'candidate_provenance.json'")
text=text.replace("assert review['archive_verified'] and review['result']['navigation_pass']", "assert review['source_archive_verified']\nassert '29 passed' in (root/'logs/reliability_combined_observation_checks_owned_20261007/regressions.log').read_text()\nassert json.loads((root/'logs/reliability_combined_gate_pause_contract_20261007/report.json').read_text())['passed']")
text=text.replace("review['archive_sha256']","review['source_archive_sha256']")
text=text.replace("provenance['missing_assets_recovered_from_verified_archive']","provenance['asset_sha256']")
text=text.replace('ros_domain=180+i','ros_domain=210+i')
old="[(c,s) for c in ('calm','field') for s in range(1,6)]"
assert text.count(old)==1;text=text.replace(old,"[('field',4),('field',5),('calm',5)]")
write('run_combined_observation_batch_20261007.py',text)
print('Prepared exact-source checks and field 4, field 5, calm 5 trial batch')
