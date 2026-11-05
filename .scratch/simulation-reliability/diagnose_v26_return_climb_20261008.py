"""Archive the fresh-pose prerequisite failure without upgrading its grade."""
import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from qualification_evidence import recorded_disarm
run=root/'logs/reliability_reduced_v26_targeted_20261008/my_world_random_s3'
rows=[json.loads(s) for s in (run/'onboard.jsonl').open()]
failure=next(r for r in rows if r.get('mission')=='FAILED')
pose=failure['pose']['data'];stamp=pose['header']['stamp'];capture=stamp['sec']+stamp['nanosec']*1e-9
disarm=recorded_disarm(rows);assert disarm
grade=json.loads((run/'navigation_grade.json').read_text())
review=dict(accepted_source=False,clock=failure['stamp'],measured_position=pose['pose']['position'],pose_capture=capture,
    pose_age_s=failure['stamp']-capture,configured_return_altitude_m=10.,original_climb_tolerance_m=.6,
    following_guard_min_altitude_m=9.7,connected_disarm=disarm,original_grade=grade,
    limitation='Recorder and controller subscriptions are independent; this row bounds the observed failed handover, not its exact leaf-call instant',
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [run/'onboard.jsonl',run/'stack.log',run/'navigation_grade.json',run/'source_manifest.json']})
(run/'return_climb_diagnosis.json').write_text(json.dumps(review,indent=2))
print(json.dumps(dict(position=review['measured_position'],pose_age_s=review['pose_age_s'],failures=[k for k,v in grade['checks'].items() if not v],connected_disarm=disarm),indent=2))
