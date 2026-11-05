import sys
from pathlib import Path
root=Path.cwd();sys.path[:0]=[str(root/'sim'),str(root/'src/aerothon_mission/mission_bt'),str(root/'src/aerothon_avoidance/avoidance')]
import test_search_current_command as test
old={};exec((root/'.scratch/reduced_scope_v12_candidate_20261008/src/aerothon_mission/mission_bt/mission_bt/search_braking.py').read_text(encoding='utf-8'),old)
original=test.make_stage
def stage_with_original_gate():
 stage,mav,now=original();stage._search_braking_gate=old['SearchBrakingGate']();return stage,mav,now
test.make_stage=stage_with_original_gate
test.test_motion_between_leaf_ticks_resets_the_fcu_settled_streak()
