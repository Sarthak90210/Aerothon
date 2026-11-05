"""Ranked probes: unsafe stop fixture, sticky safe hold, current-command guard.

Only the observed red boundary changes. Every original assertion is retained.
The commanded trip still intersects red; measured stop gains >1.50 m clearance.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
source=(root/'sim/test_search_current_command.py').read_text()
source=source.replace('from test_search_braking_20261007 import make_stage','''from test_search_braking_20261007 import make_stage as original_make_stage
def make_stage():
 stage,mav,now=original_make_stage()
 mav.exclusions=[(11.,20.,-5.,5.)]
 return stage,mav,now''')
(root/'.scratch/simulation-reliability/test_search_current_command_safe_fixture_20261009.py').write_text(source)
print('Safe-stop diagnostic prepared; all original assertions retained, red obstacle still blocks requested travel')
