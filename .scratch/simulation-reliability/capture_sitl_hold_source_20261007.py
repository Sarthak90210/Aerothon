"""Read-only source excerpts for the actual GUID_OPTIONS bit meanings."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'.scratch/simulation-reliability/sitl_hold_source_observation_20261007.json'
assert not OUT.exists()
BASE=Path.home()/'aerothon_stack/src/ardupilot'
files=[]
for relative,ranges in (
    ('ArduCopter/Parameters.cpp',[(995,1002)]),
    ('ArduCopter/mode_guided.cpp',[(612,629),(775,828)]),
    ('libraries/AC_AttitudeControl/AC_PosControl.cpp',[(568,600),(625,689)]),
):
    path=BASE/relative;raw=path.read_bytes();lines=raw.decode().splitlines()
    files.append(dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),
        excerpts=[dict(first_line=a,last_line=b,lines=lines[a-1:b]) for a,b in ranges]))
report=dict(kind='read-only installed ArduPilot source semantics',files=files,
    live_observation='logs/reliability_render_shipped_s20261003_observation_repairs_20261007/guid_options_ros2_observation_20261007.json',
    limits=['Source documents installed firmware semantics; this does not independently prove every binary byte was built from these source bytes.',
            'The separate live MAVROS cache reply supplies actual configured GUID_OPTIONS=0.',
            'No parameter/control writes, firmware build, hardware query or physics change were performed.'])
OUT.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({r['path']:r['sha256'] for r in files},indent=2))
