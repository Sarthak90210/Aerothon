"""Prepare the bounded return-framing candidate; retain normal timing gates."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
base=root/'.scratch/simulation-reliability'
stems=[
 'freeze_reduced_scope_v18_20261008.py',
 'close_reduced_v18_offline_20261008.py',
 'run_reduced_v18_full_offline_20261008.sh',
 'run_reduced_v18_split_render_20261008.sh',
 'run_reduced_v18_remaining_rendered_20261008.sh',
 'verify_reduced_v18_startup_20261008.py',
 'probe_reduced_targeted_v18_20261008.py',
 'probe_reduced_targeted_v18_20261008.sh',
 'watch_v18_failed_trials_20261008.py',
 'watch_v18_failed_trials_20261008.sh',
 'watch_v18_native_failed_trials_20261008.py',
 'watch_v18_native_failed_trials_20261008.sh',
 'watch_v18_campaign_failed_trials_20261008.py',
 'watch_v18_campaign_failed_trials_20261008.sh',
 'run_reduced_v18_campaign_20261008.sh',
 'close_reduced_v18_qualification_20261008.py',
 'close_reduced_v18_targeted_20261008.py',
 'check_v18_planned_scope_20261008.py',
 'check_v18_planned_scope_20261008.sh',
 'inspect_v18_live_native_20261008.py',
 'run_v18_qualification_gates_20261008.py',
]
for stem in stems:
    text=(base/stem).read_text(encoding='utf-8').replace('v18','v19').replace('V18','V19')
    if stem.startswith('run_v18_qualification_gates'):
        text=text.replace('reliability_reduced_v17_normal_timing_retry_20261008',
                          'reliability_reduced_v18_targeted_20261008')
        text=text.replace('V17 focused trials closed','V18 focused trials closed')
    if stem.startswith(('watch_v18_native','watch_v18_campaign')) and stem.endswith('.py'):
        old="  with onboard.open('rb') as f:\n   f.seek(max(0,onboard.stat().st_size-200000 if run.name in first_arm else 0));lines=f.read().splitlines()"
        new="  try:\n   with onboard.open('rb') as f:\n    f.seek(max(0,onboard.stat().st_size-200000 if run.name in first_arm else 0));lines=f.read().splitlines()\n  except OSError:\n   continue"
        if old in text:text=text.replace(old,new)
    (base/stem.replace('v18','v19')).write_text(text,encoding='utf-8',newline='\n')
print('V19 prepared: two flight workers, then one offline suite, five native runs, reduced matrix')
