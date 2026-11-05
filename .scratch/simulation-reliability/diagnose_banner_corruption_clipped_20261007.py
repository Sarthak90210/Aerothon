"""Identify fixture conditions previously masked by retained OCR state."""
import json,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from test_perception_corruption import BannerEnvelopeTests,CameraCorruptor,conditions
out=root/'logs/reliability_banner_corruption_clipped_20261007';out.mkdir(exist_ok=False)
case=BannerEnvelopeTests('test_every_corruption_at_every_severity')
case.setUpClass();case.setUp();results=[]
try:
    assert case.identified(case.frame)
    for key,severity in conditions(5):
        details=[]
        for seed in range(3):
            passed=case.identified(CameraCorruptor({key:severity},seed=seed).apply(case.frame))
            detail=json.loads(case.detail[-1].data)
            details.append(dict(seed=seed,identified=passed,detail=detail))
        results.append(dict(key=key,severity=severity,results=details))
finally:case.tearDown();case.tearDownClass()
(out/'report.json').write_text(json.dumps(dict(cases=results,
    scope='Controlled corruption of saved rendered fixture; not flight evidence'),indent=2)+'\n')
print(json.dumps([dict(key=row['key'],severity=row['severity'],
    identified=sum(r['identified'] for r in row['results']),
    rejections=[r['detail']['reason'] for r in row['results'] if not r['identified']])
    for row in results if not all(r['identified'] for r in row['results'])]))

