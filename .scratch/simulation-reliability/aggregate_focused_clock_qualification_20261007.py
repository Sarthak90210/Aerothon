"""Keep setup errors, physical flights and diagnostic repetitions distinct."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
directories=[root/'logs/reliability_focused_clock_navigation_20261007',
             root/'logs/reliability_focused_clock_navigation_domain_retry_20261007']
actual=[];setup=[]
for directory in directories:
    report=json.loads((directory/'report.json').read_text())
    assert report['source_unchanged']
    for result in report['results']:
        if result.get('sim_s') is None:
            setup.append(dict(source=str(directory.relative_to(root)),result=result));continue
        grade=json.loads((directory/result['run']/'navigation_grade.json').read_text())
        actual.append(dict(run=result['run'],output=str((directory/result['run']).relative_to(root)),
            navigation_pass=grade['pass_navigation'],clearance_m=grade['measured_corridor_clearance_m'],
            flight_s=grade['full_grade']['flight_time_s'],contacts=result['contacts'],
            final_armed=grade['full_grade']['final_armed'],failures=result['navigation_failures']))
assert len(actual)==10 and len({r['run'] for r in actual})==10 and len(setup)==6
repetition=root/'logs/reliability_motion_forecast_navigation_s3_20261007'
review=json.loads((repetition/'source_archive_review.json').read_text())
assert review['archive_verified']
out=root/'logs/reliability_focused_clock_aggregate_20261007';out.mkdir(exist_ok=False)
report=dict(actual_flights=actual,physical_flights=len(actual),navigation_passes=sum(r['navigation_pass'] for r in actual),
    setup_errors=setup,setup_errors_count=len(setup),source_unchanged=True,
    instrumented_calm_seed3_repetition=dict(output=str(repetition.relative_to(root)),
        source_archive=review,does_not_replace_original_failure=True),
    production_controller_adopted=False,changing_gusts_qualified=False,
    rendered_perception_qualified=False,motor_delivery_qualified=False,
    note='ROS scheduling is not fixed by the weather seed; one later passing repetition does not close an earlier clearance failure')
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
(out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(actual_flights=len(actual),navigation_passes=report['navigation_passes'],setup_errors=len(setup))))
