"""Reuse checked trial machinery with the isolated deadline candidate."""
from pathlib import Path
here=Path(__file__).parent
source=(here/'prepare_tracking_margin_candidate_20261007.py').read_text()
start=source.index('here = Path(__file__).parent')
code=source[start:source.index("print(json.dumps",start)]
code=code.replace('tracking_margin','command_deadline')
code=code.replace("assert '5 passed' in (root/'logs/reliability_lidar_fault_continuity_source_20261007/after.log').read_text()",
    "assert '4 passed' in (root/'logs/reliability_command_deadline_source_20261007/after.log').read_text()")
code=code.replace("'ros_domain=218+i'","'ros_domain=225+i'")
exec(compile(code,'<new deadline trial launcher>','exec'),dict(__file__=str(Path(__file__).resolve()),Path=Path))
root=here.parents[1]
old=here/'close_combined_observation_batch_20261007.py'
text=old.read_text().replace('combined_observation_focused_navigation','lidar_fault_continuity_navigation')
text=text.replace('combined_observation_navigation_source','lidar_fault_continuity_source')
text=text.replace('combined_observation_motion_candidate','lidar_fault_continuity_candidate')
(here/'close_lidar_fault_continuity_batch_20261007.py').write_bytes(text.encode())
print('Prepared deadline regressions and three physical navigation repeats')
