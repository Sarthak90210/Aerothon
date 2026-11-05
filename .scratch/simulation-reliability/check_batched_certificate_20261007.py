"""Check identical geometry verdicts and actual publication decisions/timing."""
import hashlib
import json
import math
import sys
import time
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/command_deadline_candidate_20261007'
sys.path[:0]=[str(snapshot/'src/aerothon_avoidance/avoidance'),str(root/'sim')]
from avoidance.local_planner import LocalPlanner
from avoidance.velocity_controller import VelocityController
from batched_certificate_candidate_20261007 import install,sample_segment,polyline_clear
from test_local_planner import wall_scan
out=root/'logs/reliability_batched_certificate_equivalence_20261007';out.mkdir(exist_ok=False)
rng=np.random.default_rng(1001)
cases=[]
for i in range(400):
    planner=LocalPlanner()
    planner.observe(*wall_scan(float(rng.uniform(.65,1.8)),float(rng.uniform(.65,1.8))))
    points=np.cumsum(rng.normal(0,.05,(16,2)),axis=0)
    points=np.vstack([[0.,0.],points])
    expected=all(planner.segment_clear(a,b) for a,b in zip(points,points[1:]))
    actual=polyline_clear(planner,[sample_segment(a,b) for a,b in zip(points,points[1:])])
    assert actual==expected,(i,actual,expected)
    cases.append(dict(index=i,expected=expected,actual=actual))
install(VelocityController,out/'source_override')
# Timing/regressions execute real publication and fresh-observation contract.
import pytest
code=pytest.main(['-q',*[str(root/'sim'/name) for name in
    ('test_corridor_clearance_contract.py','test_yaw_motion_certification.py','test_fcu_navigation_velocity.py')]])
report=dict(equivalent_polyline_cases=len(cases),verdict_mismatches=0,regression_exit_code=int(code),
    production_modified=False,physical_fixture_changed=False,clearance_limits_changed=False,
    scope='Same <=5 cm segment samples and full clearance; performance candidate, no flight qualification',
    candidate_sha256=hashlib.sha256(Path(__file__).with_name('batched_certificate_candidate_20261007.py').read_bytes()).hexdigest())
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
raise SystemExit(code)
