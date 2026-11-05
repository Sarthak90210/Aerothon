from pathlib import Path
root=Path.cwd();base=root/'.scratch/simulation-reliability'
for name in ('close_reduced_v9_offline_20261008.py','run_reduced_v9_full_offline_20261008.sh','run_reduced_v9_split_render_20261008.sh','run_reduced_v9_remaining_rendered_20261008.sh','verify_reduced_v9_startup_20261008.py'):
 text=(base/name).read_text(encoding='utf-8').replace('v9','v10')
 (base/name.replace('v9','v10')).write_text(text,encoding='utf-8',newline='\n')
text=(base/'build_verify_reduced_startup_20261008.sh').read_text(encoding='utf-8').replace('verify_reduced_startup_20261008.py','verify_reduced_v10_startup_20261008.py')
(base/'build_verify_reduced_v10_startup_20261008.sh').write_text(text,encoding='utf-8',newline='\n')
