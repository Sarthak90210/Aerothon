from pathlib import Path
root=Path.cwd();base=root/'.scratch/simulation-reliability'
for name in ('close_reduced_v3_offline_20261008.py','run_reduced_v3_full_offline_20261008.sh','run_reduced_v3_split_render_20261008.sh','run_reduced_v3_remaining_rendered_20261008.sh','verify_reduced_v3_startup_20261008.py'):
 text=(base/name).read_text(encoding='utf-8').replace('v3','v9')
 if name.endswith('.sh'):
  text=text.replace('ROS_DOMAIN_ID=220','ROS_DOMAIN_ID=20').replace('ROS_DOMAIN_ID=218','AEROTHON_ACCEPTANCE_DOMAIN=30 ROS_DOMAIN_ID=30')
  if 'full_offline' in name:
   text=text.replace('export PATH="/usr/bin:/bin:$PATH"','export PATH="/home/sarthak/.nvm/versions/node/v24.18.0/bin:/usr/bin:/bin:$PATH"')
   text=text.replace('bash scripts/run_tests.sh','bash scripts/run_tests.sh 2>&1 | tee logs/reliability_reduced_v9_full_offline_20261008.log')
  if 'remaining_rendered' in name:
   text=text.replace('three_seed_closed_review.json','targeted_closed_review.json')
 if 'verify_reduced' in name:
  text=text.replace("records={}","modules.update({'mission_bt.mav_commander':'src/aerothon_mission/mission_bt/mission_bt/mav_commander.py','avoidance.local_planner':'src/aerothon_avoidance/avoidance/avoidance/local_planner.py','camera_ctrl.camera_ctrl_node':'src/aerothon_perception/camera_ctrl/camera_ctrl/camera_ctrl_node.py'})\nrecords={}")
 (base/name.replace('v3','v9')).write_text(text,encoding='utf-8',newline='\n')
print('Prepared source-gated final offline/rendered scripts; not launched')
