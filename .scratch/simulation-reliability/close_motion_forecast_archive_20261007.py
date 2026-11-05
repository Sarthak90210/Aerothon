"""Close an already completed flight after the runner's fixed-seed path error."""
import hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/motion_forecast_candidate_20261007'
out=root/'logs/reliability_motion_forecast_navigation_s3_20261007'
recorded=json.loads((out/'my_world_calm_s3/source_manifest.json').read_text())
result=json.loads((out/'summary.json').read_text())
with zipfile.ZipFile(out/'frozen_source.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
    for name,sha in sorted(recorded.items()):
        data=(snapshot/name).read_bytes();assert hashlib.sha256(data).hexdigest()==sha,name
        archive.writestr(name,data)
    archive.writestr('source_manifest.json',json.dumps(recorded,indent=2)+'\n')
with zipfile.ZipFile(out/'frozen_source.zip') as archive:
    assert all(hashlib.sha256(archive.read(name)).hexdigest()==sha for name,sha in recorded.items())
report=dict(source_files=len(recorded),archive_verified=True,
    archive_sha256=hashlib.sha256((out/'frozen_source.zip').read_bytes()).hexdigest(),
    result=result,rendered_perception_qualified=False,motor_delivery_qualified=False,
    runner_closure_error='Runner read my_world_calm_s1 instead of actual my_world_calm_s3; flight untouched',
    diagnostic_time_basis='points_body time is each integration interval start; endpoint time is time plus 0.05 s')
(out/'source_archive_review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(source_files=len(recorded),archive_verified=True,
                     navigation_pass=result['navigation_pass'])))
