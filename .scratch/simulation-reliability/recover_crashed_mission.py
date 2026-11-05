"""Operator recovery of this failed simulator run through the FCU LAND mode."""
import json
import time
from pathlib import Path
from pymavlink import mavutil

out=Path('logs/reliability_render_my_world_s20261003_retry1_20261005')
link=mavutil.mavlink_connection('udpout:127.0.0.1:14552',source_system=253)
link.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS,
                        mavutil.mavlink.MAV_AUTOPILOT_INVALID,0,0,0)
heartbeat=None
until=time.monotonic()+60
while time.monotonic()<until:
    msg=link.recv_match(type='HEARTBEAT',blocking=True,timeout=5)
    if msg is not None and msg.get_srcSystem()==1 and msg.get_srcComponent()==1:
        heartbeat=msg
        link.target_system=1
        link.target_component=1
        break
if heartbeat is None:
    raise SystemExit('Simulator FCU heartbeat unavailable; no command sent')
mode=link.mode_mapping()['LAND']
link.set_mode(mode)
(out/'operator_recovery.json').write_text(json.dumps(dict(
    reason="mission node crashed: optional camera detection missing x/y",
    command='LAND',target_system=link.target_system,
    target_component=link.target_component,wall_epoch=time.time(),
    acceptance_pass=False,source='operator simulator recovery; not autonomous mission completion'),indent=2))
until=time.monotonic()+180
while time.monotonic()<until:
    msg=link.recv_match(type='HEARTBEAT',blocking=True,timeout=5)
    if msg is not None and msg.get_srcSystem()==1:
        print(json.dumps(dict(mode=msg.custom_mode,armed=bool(msg.base_mode & 128))),flush=True)
        if not msg.base_mode & 128:
            break
else:
    raise SystemExit('Recovery disarm not observed within wall timeout')
link.close()
