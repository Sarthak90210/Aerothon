"""Prepare the remaining calm/field seeds after the exact-source focus closes."""
from pathlib import Path
here=Path(__file__).parent
source=(here/'run_command_deadline_verified_batch_20261007.py').read_text()
source=source.replace('logs/reliability_command_deadline_navigation_20261007','logs/reliability_command_deadline_extended_navigation_20261007')
old="[('field',4),('field',5),('calm',5)]"
assert source.count(old)==1
source=source.replace(old,"[('calm',1),('calm',2),('calm',3),('calm',4),('field',1),('field',2),('field',3)]")
source=source.replace('ros_domain=225+i','ros_domain=170+i')
anchor="review=json.loads((qualified/'candidate_provenance.json').read_text())"
assert source.count(anchor)==1
guard='''focus=root/'logs/reliability_command_deadline_navigation_20261007'
focus_report=json.loads((focus/'report.json').read_text())
assert focus_report['finished_wall'] and focus_report['source_unchanged'] and focus_report['all_navigation_pass']
assert len(focus_report['results'])==3
for result in focus_report['results']:
    grade=json.loads((focus/result['run']/'navigation_grade.json').read_text())
    assert grade['pass_navigation'] and grade['measured_corridor_clearance_m']>=.725
    assert grade['full_grade']['final_armed'] is False
'''
source=source.replace(anchor,guard+anchor)
(here/'run_command_deadline_extended_batch_20261007.py').write_bytes(source.encode())
close=(here/'close_lidar_fault_continuity_batch_20261007.py').read_text()
for old,new in {'lidar_fault_continuity_navigation':'command_deadline_navigation',
    'lidar_fault_continuity_source':'command_deadline_source',
    'lidar_fault_continuity_candidate':'command_deadline_candidate'}.items():close=close.replace(old,new)
(here/'close_command_deadline_batch_20261007.py').write_bytes(close.encode())
print('Prepared seven additional calm/field seeds, guarded by all three focused navigation/reserve passes')
