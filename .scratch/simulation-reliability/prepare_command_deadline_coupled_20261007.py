"""Keep exact strong-gust fixtures; declare their frozen computation clock."""
from pathlib import Path
here=Path(__file__).parent
source=(here/'check_buffered_scan_coupled_20261007.py').read_text()
for old,new in {
    '.scratch/buffered_scan_motion_candidate_20261007':'.scratch/command_deadline_candidate_20261007',
    'logs/reliability_buffered_stamped_fixture_preparation_20261007/rejected_regression_source.zip':'logs/reliability_command_deadline_source_20261007/frozen_source.zip',
    'logs/reliability_buffered_scan_coupled_20261007':'logs/reliability_command_deadline_coupled_20261007',
}.items():
    assert old in source;source=source.replace(old,new)
old='def initialized(node,*a,**kw):initialize(node,*a,**kw);buffered_scan_pose.install(node)'
assert source.count(old)==1
source=source.replace(old,'''def initialized(node,*a,**kw):
    initialize(node,*a,**kw);buffered_scan_pose.install(node)
    from rclpy.parameter import Parameter
    node.set_parameters([Parameter('motion_computation_budget_s',value=0.)])''')
(here/'check_command_deadline_coupled_20261007.py').write_bytes(source.encode())
print('Preserved coupled physics, zero offline computation time, no production edits')
