"""Advance only a closed isolated experiment to explicit restore configuration."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
closed=json.loads((root/'logs/reliability_braked_navigation_candidate_scoped_owned_20261007/status.json').read_text())
assert closed['state']=='FAILED' and closed['exit_code']==1
snapshot=root/'.scratch/braked_navigation_candidate_20261007'
module=snapshot/'src/aerothon_mission/mission_bt/mission_bt/gate_braking_candidate.py'
candidate=root/'.scratch/simulation-reliability/gate_advance_braking_candidate_20261007.py'
module.write_bytes(candidate.read_bytes())
path=snapshot/'candidate_provenance.json'
provenance=json.loads(path.read_text())
sha=lambda file:hashlib.sha256(file.read_bytes()).hexdigest()
provenance.update(candidate_source_sha256=sha(candidate),restore_speed_mps=5.,
    restore_basis='explicit commanded navigation configuration when no prior speed command exists')
provenance['modified'].update({str(module.relative_to(snapshot)):sha(module),
    'sim/navigation_mission.py':sha(snapshot/'sim/navigation_mission.py')})
path.write_text(json.dumps(provenance,indent=2)+'\n')
print(json.dumps(provenance))
