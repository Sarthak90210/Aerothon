import json
from pathlib import Path
report=json.loads(Path('logs/reliability_moving_measurement_time_loss_20261006.json').read_text())
first=report['first_native_violation']['stamp'];handover=report['handover']['transition_stamp']
window=report['failure_window']
start=next(r for r in window if r['braking'] is False)
print(json.dumps(dict(handover_stamp=handover,first_violation_stamp=first,seconds_after_handover=first-handover,first_no_certified_braking_in_window=start,claim='Later stopping viability remains unqualified; timing alone does not prove a separate cause'),indent=2))