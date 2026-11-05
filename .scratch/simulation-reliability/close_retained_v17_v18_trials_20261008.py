"""Close retained diagnostic runs without upgrading their failed grades."""
import hashlib,json,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from qualification_evidence import recorded_disarm
for version,folder,label in [
 ('v17','reliability_reduced_v17_normal_timing_retry_20261008','normal_timing_retry_closed_review'),
 ('v18','reliability_reduced_v18_targeted_20261008','targeted_failure_closed_review'),
 ('v19','reliability_reduced_v19_targeted_20261008','targeted_failure_closed_review'),
 ('v20','reliability_reduced_v20_targeted_20261008','targeted_failure_closed_review'),
 ('v22','reliability_reduced_v22_targeted_20261008','targeted_failure_closed_review'),
 ('v23','reliability_reduced_v23_targeted_20261008','targeted_failure_closed_review'),
 ('v24','reliability_reduced_v24_targeted_20261008','targeted_failure_closed_review'),
 ('v25','reliability_reduced_v25_targeted_20261008','targeted_failure_closed_review'),
 ('v26','reliability_reduced_v26_targeted_20261008','targeted_failure_closed_review'),
 ('v27','reliability_reduced_v27_targeted_20261008','targeted_failure_closed_review'),
 ('v28','reliability_reduced_v28_targeted_20261008','targeted_failure_closed_review'),
 ('v29','reliability_reduced_v29_targeted_20261008','targeted_failure_closed_review'),
 ('v30','reliability_reduced_v30_targeted_20261008','targeted_failure_closed_review'),
 ('v31','reliability_reduced_v31_targeted_20261008','targeted_failure_closed_review'),
 ('v33','reliability_reduced_v33_targeted_20261008','targeted_failure_closed_review'),
 ('v34','reliability_reduced_v34_targeted_20261008','targeted_failure_closed_review'),
 ('v35','reliability_reduced_v35_targeted_20261008','targeted_failure_closed_review'),
 ('v36','reliability_reduced_v36_targeted_20261008','targeted_failure_closed_review')]:
    parent=root/'logs'/folder
    if not (parent/'report.json').exists():continue
    source=root/'logs'/f'reliability_reduced_scope_{version}_source_20261008'
    destination=source/f'{label}.json'
    if destination.exists():continue
    report=json.loads((parent/'report.json').read_text())
    snapshot=root/'.scratch'/f'reduced_scope_{version}_candidate_20261008'
    manifest=json.loads((snapshot/'source_manifest.json').read_text())
    provenance=json.loads((source/'provenance.json').read_text())
    assert hashlib.sha256((source/'frozen_source.zip').read_bytes()).hexdigest()==provenance['archive_sha256']
    with zipfile.ZipFile(source/'frozen_source.zip') as archive:
        for name,sha in manifest.items():
            assert hashlib.sha256(archive.read(name)).hexdigest()==sha,name
            assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha,name
    records=[]
    for result in report['results']:
        run=parent/result['run']
        assert json.loads((run/'source_manifest.json').read_text())==manifest
        rows=[json.loads(line) for line in (run/'onboard.jsonl').read_text().splitlines()]
        disarm=recorded_disarm(rows);assert disarm,run
        stop=run/'operator_stop.json'
        records.append(dict(result=result,grade=json.loads((run/'navigation_grade.json').read_text()),
            configuration=json.loads((run/'configuration.json').read_text()),connected_disarm=disarm,
            operator_stop=json.loads(stop.read_text()) if stop.exists() else None,
            files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                   for p in run.iterdir() if p.is_file()}))
    review=dict(accepted_source=False,qualification_complete=False,pass_navigation=report['pass_navigation'],
        source_archive_verified=True,source_files=len(manifest),source_unchanged=report['source_unchanged'],
        concurrent_flights=2,full_offline_suite_concurrent=False,results=records,
        fixture_delivery_qualified=False,rendered_qualified=False)
    with destination.open('x') as f:json.dump(review,f,indent=2)
    print(str(destination))
