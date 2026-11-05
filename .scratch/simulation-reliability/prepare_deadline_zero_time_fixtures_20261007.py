"""Declare zero computation time only for frozen-clock offline physics fixtures."""
from pathlib import Path
here=Path(__file__).parent
source=(here/'check_command_deadline_regressions_20261007.py').read_text()
old='    original(node,*args,**kwargs);buffered_scan_pose.install(node)'
assert source.count(old)==1
new='''    original(node,*args,**kwargs);buffered_scan_pose.install(node)
    # These physical fixtures advance time only after _tick returns. Their
    # computation interval is exactly zero, unlike the independent-clock
    # mission trials, which retain the candidate's 0.20 s declared budget.
    from rclpy.parameter import Parameter
    node.set_parameters([Parameter('motion_computation_budget_s',value=0.)])'''
source=source.replace(old,new)
(here/'check_command_deadline_zero_time_regressions_20261007.py').write_bytes(source.encode())
runner=(here/'run_command_deadline_batch_20261007.py').read_text()
runner=runner.replace('reliability_command_deadline_trials_owned_20261007','reliability_command_deadline_zero_time_checks_owned_20261007')
(here/'run_command_deadline_verified_batch_20261007.py').write_bytes(runner.encode())
script='''#!/usr/bin/env bash
set -eo pipefail
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=222 ROS_LOCALHOST_ONLY=1
/usr/bin/python3 .scratch/simulation-reliability/check_command_deadline_zero_time_regressions_20261007.py > logs/reliability_command_deadline_zero_time_checks_owned_20261007/regressions.log 2>&1
exec /usr/bin/python3 .scratch/simulation-reliability/run_command_deadline_verified_batch_20261007.py
'''
(here/'run_command_deadline_zero_time_checks_20261007.sh').write_bytes(script.encode())
print('Declared offline computation time zero; physical delay .4 s and response .6 s unchanged; live budget .20 s unchanged')
