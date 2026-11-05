"""Aggregate every preserved navigation result without changing grades."""
from collections import Counter
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
campaign = root / 'logs/reliability_navigation_baseline_matrix_assets_20261006'
results = json.loads((campaign/'summary.json').read_text())
classified = json.loads((campaign/'classification.json').read_text())
worlds = {}
for result in results:
    world, conditions, seed = result['run'].rsplit('_', 2)
    item = worlds.setdefault(world, dict(trials=0, navigation_passes=0, contacts=0,
        flights_with_contacts=0, results=Counter(), failed_checks=Counter(), minimum_clearance_m=None))
    item['trials'] += 1
    item['navigation_passes'] += bool(result.get('navigation_pass'))
    item['contacts'] += result.get('contacts',0)
    item['flights_with_contacts'] += result.get('contacts',0)>0
    item['results'][result['result']] += 1
    item['failed_checks'].update(result.get('navigation_failures',[]))
    grade_path = campaign/result['run']/'navigation_grade.json'
    if grade_path.exists():
        value=json.loads(grade_path.read_text()).get('measured_corridor_clearance_m')
        if value is not None:
            current=item['minimum_clearance_m']
            item['minimum_clearance_m']=value if current is None else min(current,value)
report = dict(requested_trials=len(classified)*20, executed_trials=len(results),
    navigation_passes=sum(bool(result.get('navigation_pass')) for result in results),
    flights_with_contacts=sum(result.get('contacts',0)>0 for result in results),
    result_counts=dict(Counter(result['result'] for result in results)),
    failed_check_counts=dict(Counter(check for result in results for check in result.get('navigation_failures',[]))),
    classified_without_flight=[dict(world=item['world'],combinations=20,
        classification=item['classification'],validation_errors=item['validation_errors'])
        for item in classified if item['classification']!='navigation trial required'],
    worlds=worlds, scope='Frozen qualified-source baseline characterization; all original grades unchanged',
    limitations=['Headless velocity telemetry omits wind-induced ground motion.',
        'Prior position target is cleared before first delayed velocity receipt.',
        'Failed runs can stop before recording/publishing the final disarmed sample.',
        'Headless results do not qualify rendered perception or motor delivery.'])
destination=campaign/'aggregate_review_20261007.json'
with destination.open('x') as output:
    output.write(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
