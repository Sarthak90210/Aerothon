"""Archive the local FCU source backing the normal GPS LAND model correction."""
import hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_land_model_primary_source_20261008';out.mkdir(exist_ok=False)
ap=Path('/home/sarthak/ardupilot')
paths=['ArduCopter/mode_land.cpp','ArduCopter/mode.cpp','libraries/AC_AttitudeControl/AC_PosControl.cpp']
records=[]
for name in paths:
    data=(ap/name).read_bytes();target=out/Path(name).name;target.write_bytes(data)
    records.append(dict(path=str(ap/name),archive=target.name,sha256=hashlib.sha256(data).hexdigest()))
commit=subprocess.check_output(['git','-C',str(ap),'rev-parse','HEAD'],text=True).strip()
status=subprocess.check_output(['git','-C',str(ap),'status','--porcelain','--',*paths],text=True)
record=dict(ardupilot_commit=commit,source_status=status,files=records,
    evidence='GPS LAND runs the horizontal position controller; zero pilot correction is input to the position controller, not an open horizontal airframe velocity command',
    interpretation='Headless model retains its existing proportional position controller, actuator response, wind, estimator errors and vertical descent; estimated XY is latched on entry and repeated LAND commands cannot relatch it. This is an object-level model, not full EKF or rotor aerodynamics.')
(out/'primary_source_review.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
