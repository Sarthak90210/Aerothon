"""Apply the pause contract to the exact frozen gate implementation."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
template=Path(__file__).with_name('check_gate_observation_pause_20261007.py').read_text()
replacements={
    "str(root/'src/aerothon_mission/mission_bt')":"str(root/'.scratch/gate_pause_motion_candidate_20261007/src/aerothon_mission/mission_bt')",
    'reliability_gate_observation_pause_contract_20261007':'reliability_gate_pause_inline_contract_20261007',
    'from gate_observation_pause_candidate_20261007 import ObservationPausedGateAdvance':
        'from mission_bt.gate_braking_candidate import BrakedGateAdvance as ObservationPausedGateAdvance',
    "module=Path(__file__).with_name('gate_observation_pause_candidate_20261007.py')":
        "module=root/'.scratch/gate_pause_motion_candidate_20261007/src/aerothon_mission/mission_bt/mission_bt/gate_braking_candidate.py'",
}
for old,new in replacements.items():
    assert template.count(old)==1,old
    template=template.replace(old,new)
exec(compile(template,str(Path(__file__).resolve()),'exec'),globals())
(root/'logs/reliability_gate_pause_inline_contract_20261007/executed_contract.py').write_text(template)
