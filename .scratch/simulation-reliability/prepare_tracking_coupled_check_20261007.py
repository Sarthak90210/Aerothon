"""Use exactly the preserved coupled physics and stamped sensor fixtures."""
from pathlib import Path
here = Path(__file__).parent
source = (here/'check_buffered_scan_coupled_20261007.py').read_text()
replacements = {
    '.scratch/buffered_scan_motion_candidate_20261007': '.scratch/tracking_margin_candidate_20261007',
    'logs/reliability_buffered_stamped_fixture_preparation_20261007/rejected_regression_source.zip': 'logs/reliability_tracking_margin_source_20261007/frozen_source.zip',
    'logs/reliability_buffered_scan_coupled_20261007': 'logs/reliability_tracking_margin_coupled_20261007',
}
for old, new in replacements.items():
    assert old in source
    source = source.replace(old, new)
with (here/'check_tracking_margin_coupled_20261007.py').open('xb') as stream:
    stream.write(source.encode())
with (here/'run_tracking_margin_coupled_20261007.sh').open('xb') as stream:
    stream.write(b'''#!/usr/bin/env bash
set -eo pipefail
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=221 ROS_LOCALHOST_ONLY=1
/usr/bin/python3 .scratch/simulation-reliability/check_tracking_margin_contract_20261007.py > logs/reliability_tracking_margin_coupled_owned_20261007/contract.log 2>&1
exec /usr/bin/python3 .scratch/simulation-reliability/check_tracking_margin_coupled_20261007.py
''')
