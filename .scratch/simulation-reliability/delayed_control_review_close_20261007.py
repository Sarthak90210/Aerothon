"""Close scratch experiments without changing any grade or production source."""
import hashlib
import json
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parents[2]
scratch=root/'.scratch/simulation-reliability'
outputs=(
    ('receipt_tracking_dirty0','logs/delayed_control_review_smith_dirty0_20261007.json'),
    ('early_hold_late1','logs/delayed_control_review_early_hold_late1_20261007.json'),
    ('feedback_reserved_dirty0','logs/delayed_control_review_feedback_reserved_dirty0_20261007.json'),
)
results=[]
for label,name in outputs:
    report=json.loads((root/name).read_text())
    rows=report['rows']
    violations=[r for r in rows if r['independent_clearance_m']<.70]
    uncertified=[r for r in rows if r['detail'].get('braking_clearance_available') is False]
    stuck=[r for r in rows if r['detail']['state']=='STUCK']
    actual_min=report.get('minimum_actual_clearance_m')
    component_hold=(label=='early_hold_late1' and not violations and actual_min>=.70)
    results.append(dict(label=label,source=name,grade_pass=report['passed'],
        failure=report['failure'],actual_minimum_clearance_m=actual_min,
        preintegration_minimum_clearance_m=min(r['independent_clearance_m'] for r in rows),
        records=len(rows),final_observation_s=rows[-1]['stamp'],
        first_observed_clearance_violation_s=None if not violations else violations[0]['stamp'],
        first_uncertified_raw_zero_s=None if not uncertified else uncertified[0]['stamp'],
        uncertified_raw_zero_observations=len(uncertified),
        first_recovery_exhaustion_s=None if not stuck else stuck[0]['stamp'],
        finite_early_hold_component_clear=component_hold,
        traversal_qualified=False,automatic_rejection_policy_qualified=False,
        source_sha256=report['source_sha256'],options=report['diagnostic_options']))

sources=[
    root/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py',
    root/'src/aerothon_avoidance/avoidance/avoidance/local_planner.py',
    root/'src/aerothon_avoidance/avoidance/avoidance/scan_geometry.py',
    root/'src/aerothon_sim/sim_gazebo/sim_gazebo/corruptions.py',
    root/'sim/test_slalom_traverse.py',root/'sim/test_corridor_stress.py',
    scratch/'probe_gust_margin.py',
]+sorted(scratch.glob('delayed_control_review_*.py'))+sorted(scratch.glob('delayed_control_review_*.sh'))
manifest={str(p.relative_to(root)):dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in sources}
expected='76ec878ba6c5747176e6e6d5456d4295977344d75cdbc59c610451b662f40e93'
assert manifest['src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py']['sha256']==expected
for result in results:
    for name,digest in result['source_sha256'].items():
        assert name in manifest and manifest[name]['sha256']==digest,(result['label'],name)

archive=scratch/'delayed_control_review_sources_20261007.zip'
assert not archive.exists()
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
    for p in sources:
        z.writestr(str(p.relative_to(root)),p.read_bytes())
    z.writestr('exact_source_manifest.json',json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(archive) as z:
    for name,entry in manifest.items():
        assert hashlib.sha256(z.read(name)).hexdigest()==entry['sha256']
summary=dict(state='CLOSED_REJECTED_TRAVERSAL_PROTOTYPES',results=results,
    production_source_unchanged=True,original_motion_check_retained=True,
    original_minimum_clearance_m=.70,sampling_reserve_m=.025,
    native_fcu_hold_qualified=False,default_gust_traversals_passed=0,
    early_hold_component_is_finite_trial_only=True,
    uncertainty='Historical derivative point forecasts cannot bound future Gaussian disturbances.',
    archive=str(archive.relative_to(root)),
    archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    source_files=len(manifest),manifest=manifest)
out=scratch/'delayed_control_review_results_20261007.json'
assert not out.exists()
out.write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='manifest'},indent=2))
