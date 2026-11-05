from pathlib import Path
root=Path.cwd();base=root/'.scratch/simulation-reliability'
for name in ('close_reduced_v10_offline_20261008.py','run_reduced_v10_full_offline_20261008.sh','run_reduced_v10_split_render_20261008.sh','run_reduced_v10_remaining_rendered_20261008.sh','verify_reduced_v10_startup_20261008.py'):
 text=(base/name).read_text(encoding='utf-8').replace('v10','v11')
 (base/name.replace('v10','v11')).write_text(text,encoding='utf-8',newline='\n')
text=(base/'build_verify_reduced_v10_startup_20261008.sh').read_text(encoding='utf-8').replace('v10','v11').replace('colcon build --packages-select','colcon build --base-paths src/aerothon_mission/mission_bt src/aerothon_avoidance/avoidance --packages-select')
(base/'build_verify_reduced_v11_startup_20261008.sh').write_text(text,encoding='utf-8',newline='\n')
text=(base/'probe_reduced_targeted_v11_20261008.py').read_text(encoding='utf-8').replace("out=root/'logs/reliability_reduced_v11_targeted_20261008'","assert json.loads((root/'logs/reliability_reduced_v11_targeted_20261008/report.json').read_text())['pass_navigation'], 'Primary mild-weather regression has not passed'\nout=root/'logs/reliability_reduced_v11_remaining_targeted_20261008'").replace("cases=[('random',3)]","cases=[('field',1),('field',2),('field',3),('random',4)]").replace('pool.submit(worker,44+i','pool.submit(worker,40+i')
(base/'probe_reduced_remaining_v11_20261008.py').write_text(text,encoding='utf-8',newline='\n')
text=(base/'probe_reduced_targeted_v11_20261008.sh').read_text(encoding='utf-8').replace('probe_reduced_targeted_v11','probe_reduced_remaining_v11')
(base/'probe_reduced_remaining_v11_20261008.sh').write_text(text,encoding='utf-8',newline='\n')
print('Prepared remaining same-source seeds and final verification; still gated on primary regression')
