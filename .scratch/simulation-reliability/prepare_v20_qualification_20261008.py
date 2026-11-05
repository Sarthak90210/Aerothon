"""Prepare the normal-startup landing height fix after focused checks."""
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
stems=[
 'freeze_reduced_scope_v19_20261008.py','close_reduced_v19_offline_20261008.py',
 'run_reduced_v19_full_offline_20261008.sh','run_reduced_v19_split_render_20261008.sh',
 'run_reduced_v19_remaining_rendered_20261008.sh','verify_reduced_v19_startup_20261008.py',
 'probe_reduced_targeted_v19_20261008.py','probe_reduced_targeted_v19_20261008.sh',
 'watch_v19_failed_trials_20261008.py','watch_v19_failed_trials_20261008.sh',
 'watch_v19_native_failed_trials_20261008.py','watch_v19_native_failed_trials_20261008.sh',
 'watch_v19_campaign_failed_trials_20261008.py','watch_v19_campaign_failed_trials_20261008.sh',
 'run_reduced_v19_campaign_20261008.sh','close_reduced_v19_qualification_20261008.py',
 'close_reduced_v19_targeted_20261008.py','check_v19_planned_scope_20261008.py',
 'check_v19_planned_scope_20261008.sh','inspect_v19_live_native_20261008.py',
 'run_v19_qualification_gates_20261008.py']
for stem in stems:
    text=(base/stem).read_text(encoding='utf-8').replace('v19','v20').replace('V19','V20')
    if stem=='run_v19_qualification_gates_20261008.py':
        text=text.replace('reliability_reduced_v18_targeted_20261008','reliability_reduced_v19_targeted_20261008')
        text=text.replace('V18 focused trials closed','V19 focused trials closed')
    if stem=='probe_reduced_targeted_v19_20261008.py':
        text=text.replace("cases=[('field',1),('field',2),('field',3),('random',3),('random',4)]",
                          "cases=[('random',3),('field',2),('field',1),('field',3),('random',4)]")
    (base/stem.replace('v19','v20')).write_text(text,encoding='utf-8',newline='\n')
print('V20 prepared: retained random 3 and field 2 first; all five cases required')
