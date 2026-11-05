"""Reuse the physical navigation checks with only the new observer candidate."""
from pathlib import Path

here = Path(__file__).parent
def save(name, content):
    with (here/name).open('x', newline='\n') as stream:
        stream.write(content)

source = (here/'check_combined_observation_regressions_20261007.py').read_text()
source = source.replace('.scratch/combined_observation_motion_candidate_20261007', '.scratch/lidar_fault_continuity_candidate_20261007')
save('check_lidar_fault_continuity_regressions_20261007.py', source)
source = (here/'run_combined_observation_batch_20261007.py').read_text()
replacements = {
    '.scratch/combined_observation_motion_candidate_20261007': '.scratch/lidar_fault_continuity_candidate_20261007',
    'logs/reliability_combined_observation_navigation_source_20261007': 'logs/reliability_lidar_fault_continuity_source_20261007',
    'logs/reliability_combined_observation_focused_navigation_20261007': 'logs/reliability_lidar_fault_continuity_navigation_20261007',
    'logs/reliability_combined_observation_checks_owned_20261007/regressions.log': 'logs/reliability_lidar_fault_continuity_trials_owned_20261007/regressions.log',
    'ros_domain=210+i': 'ros_domain=215+i',
}
for old, new in replacements.items():
    assert old in source, old
    source = source.replace(old, new)
source = source.replace("assert json.loads((root/'logs/reliability_combined_gate_pause_contract_20261007/report.json').read_text())['passed']", 
    "assert '5 passed' in (qualified/'after.log').read_text()")
save('run_lidar_fault_continuity_batch_20261007.py', source)
save('run_lidar_fault_continuity_trials_20261007.sh', '''#!/usr/bin/env bash
set -eo pipefail
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=224 ROS_LOCALHOST_ONLY=1
/usr/bin/python3 .scratch/simulation-reliability/check_lidar_fault_continuity_regressions_20261007.py > logs/reliability_lidar_fault_continuity_trials_owned_20261007/regressions.log 2>&1
exec /usr/bin/python3 .scratch/simulation-reliability/run_lidar_fault_continuity_batch_20261007.py
''')
print('Prepared 29 controller checks and field 4, field 5, calm 5 physical trials')
