"""Prepare exact-source qualification after the passive recording-only fix."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
base=root/'.scratch/simulation-reliability'
stems=[
'freeze_reduced_scope_v16_20261008.py',
'close_reduced_v16_offline_20261008.py','run_reduced_v16_full_offline_20261008.sh',
'run_reduced_v16_split_render_20261008.sh','run_reduced_v16_remaining_rendered_20261008.sh',
'verify_reduced_v16_startup_20261008.py','build_verify_reduced_v16_startup_20261008.sh',
'probe_reduced_targeted_v16_20261008.py','probe_reduced_targeted_v16_20261008.sh',
'watch_v16_failed_trials_20261008.py','watch_v16_failed_trials_20261008.sh',
'watch_v16_native_failed_trials_20261008.py','watch_v16_native_failed_trials_20261008.sh',
'watch_v16_campaign_failed_trials_20261008.py','watch_v16_campaign_failed_trials_20261008.sh',
'run_reduced_v16_campaign_20261008.sh','close_reduced_v16_qualification_20261008.py',
'close_reduced_v16_targeted_20261008.py','check_v16_planned_scope_20261008.py','check_v16_planned_scope_20261008.sh',
'run_v16_rendered_after_split_20261008.py','inspect_v16_live_native_20261008.py']
for stem in stems:
    text=(base/stem).read_text(encoding='utf-8').replace('v16','v17').replace('V16','V17')
    if stem=='probe_reduced_targeted_v16_20261008.py':
        text=text.replace("cases=[('random',3)]","cases=[('random',3),('field',1),('field',2),('field',3),('random',4)]")
        text=text.replace('max_workers=2','max_workers=5').replace('pool.submit(worker,44+i,cases[i::2]) for i in (0,1)','pool.submit(worker,40+i,cases[i::5]) for i in range(5)')
        text=text.replace('Primary mild-weather regression','Five normal-timing targeted navigation regressions')
    if stem=='close_reduced_v16_targeted_20261008.py':
        text=text.replace("parent=root/('logs/reliability_reduced_v17_targeted_20261008' if (weather,seed)==('random',3) else 'logs/reliability_reduced_v17_remaining_targeted_20261008')","parent=root/'logs/reliability_reduced_v17_targeted_20261008'")
    (base/stem.replace('v16','v17')).write_text(text,encoding='utf-8',newline='\n')
print('Prepared V17 gates; contact grader and all safety thresholds unchanged')
