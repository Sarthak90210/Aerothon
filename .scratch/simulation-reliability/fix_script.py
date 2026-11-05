from pathlib import Path
p=Path('.scratch/simulation-reliability/check_iteration.sh');s=p.read_text().replace('PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=214','PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=216').replace('PYTHONNOUSERSITE=1\n','PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=216\n');p.write_bytes(s.encode())
