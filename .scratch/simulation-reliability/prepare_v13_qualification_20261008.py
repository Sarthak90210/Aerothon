from pathlib import Path
root=Path.cwd();base=root/'.scratch/simulation-reliability'
for stem in ('close_reduced_v12_offline_20261008.py','run_reduced_v12_full_offline_20261008.sh','run_reduced_v12_split_render_20261008.sh','run_reduced_v12_remaining_rendered_20261008.sh','verify_reduced_v12_startup_20261008.py','build_verify_reduced_v12_startup_20261008.sh'):
 text=(base/stem).read_text(encoding='utf-8').replace('v12','v13')
 (base/stem.replace('v12','v13')).write_text(text,encoding='utf-8',newline='\n')
text=(base/'probe_reduced_targeted_v13_20261008.py').read_text(encoding='utf-8').replace("out=root/'logs/reliability_reduced_v13_targeted_20261008'","assert json.loads((root/'logs/reliability_reduced_v13_targeted_20261008/report.json').read_text())['pass_navigation'], 'Primary mild-weather regression has not passed'\nout=root/'logs/reliability_reduced_v13_remaining_targeted_20261008'").replace("cases=[('random',3)]","cases=[('field',1),('field',2),('field',3),('random',4)]").replace('pool.submit(worker,44+i','pool.submit(worker,40+i').replace('Primary mild-weather regression','Four remaining targeted regressions')
(base/'probe_reduced_remaining_v13_20261008.py').write_text(text,encoding='utf-8',newline='\n')
text=(base/'probe_reduced_targeted_v13_20261008.sh').read_text(encoding='utf-8').replace('probe_reduced_targeted_v13','probe_reduced_remaining_v13')
(base/'probe_reduced_remaining_v13_20261008.sh').write_text(text,encoding='utf-8',newline='\n')
for suffix in ('py','sh'):
 text=(base/f'watch_v13_failed_trials_20261008.{suffix}').read_text(encoding='utf-8').replace('reliability_reduced_v13_targeted','reliability_reduced_v13_remaining_targeted').replace('watch_v13_failed','watch_v13_remaining_failed')
 (base/f'watch_v13_remaining_failed_trials_20261008.{suffix}').write_text(text,encoding='utf-8',newline='\n')
for suffix in ('py','sh'):
 text=(base/f'check_v8_planned_scope_20261008.{suffix}').read_text(encoding='utf-8').replace('v8','v13')
 (base/f'check_v13_planned_scope_20261008.{suffix}').write_text(text,encoding='utf-8',newline='\n')
print('Prepared gated V12 qualification scripts; native capture rate remains 20 Hz')
