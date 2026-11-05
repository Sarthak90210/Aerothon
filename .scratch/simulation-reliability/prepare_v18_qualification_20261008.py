"""Freeze the normal LAND model correction and gate resource-bounded runs."""
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
stems=['freeze_reduced_scope_v17_20261008.py','close_reduced_v17_offline_20261008.py','run_reduced_v17_full_offline_20261008.sh','run_reduced_v17_split_render_20261008.sh','run_reduced_v17_remaining_rendered_20261008.sh','verify_reduced_v17_startup_20261008.py','probe_reduced_targeted_v17_20261008.py','probe_reduced_targeted_v17_20261008.sh','watch_v17_retry_failed_trials_20261008.py','watch_v17_retry_failed_trials_20261008.sh','watch_v17_native_failed_trials_20261008.py','watch_v17_native_failed_trials_20261008.sh','watch_v17_campaign_failed_trials_20261008.py','watch_v17_campaign_failed_trials_20261008.sh','run_reduced_v17_campaign_20261008.sh','close_reduced_v17_qualification_20261008.py','close_reduced_v17_targeted_20261008.py','check_v17_planned_scope_20261008.py','check_v17_planned_scope_20261008.sh','inspect_v17_live_native_20261008.py']
for stem in stems:
    text=(base/stem).read_text(encoding='utf-8').replace('v17','v18').replace('V17','V18')
    destination=stem.replace('v17','v18')
    if stem=='probe_reduced_targeted_v17_20261008.py':
        text=text.replace("cases=[('random',3),('field',1),('field',2),('field',3),('random',4)]","cases=[('field',1),('field',2),('field',3),('random',3),('random',4)]")
        text=text.replace('max_workers=5','max_workers=2').replace('pool.submit(worker,40+i,cases[i::5]) for i in range(5)','pool.submit(worker,40+i,cases[i::2]) for i in range(2)')
    if 'watch_v17_retry_failed_trials' in stem:
        text=text.replace('reliability_reduced_v18_normal_timing_retry_20261008','reliability_reduced_v18_targeted_20261008').replace('watch_v18_retry_failed','watch_v18_failed')
        destination=destination.replace('watch_v18_retry_failed','watch_v18_failed')
    if stem=='run_reduced_v17_campaign_20261008.sh':text=text.replace('-j 6','-j 2')
    (base/destination).write_text(text,encoding='utf-8',newline='\n')
print('V18 prepared: two independent flights; no simultaneous full suite/native stack')
