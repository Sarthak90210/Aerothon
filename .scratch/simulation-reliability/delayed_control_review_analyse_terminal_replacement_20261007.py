import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parents[2]
path=root/'logs/delayed_control_review_terminal_replacement_dirty0_20261007.json'
report=json.loads(path.read_text())
rows=report['rows']
comparisons=report['certificate_comparisons']
first_breach=next((r for r in rows if r['independent_clearance_m']<.70),None)
benefit=[r for r in comparisons if r['corrected'] and not r['legacy']]
stronger=[r for r in comparisons if not r['corrected'] and r['legacy']]
refusals=[r for r in rows if r['detail'].get('braking_clearance_available') is False]
summary=dict(source=str(path.relative_to(root)),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    passed=report['passed'],failure=report['failure'],
    actual_minimum_clearance_m=report['minimum_actual_clearance_m'],
    observations=len(rows),final_observation_s=rows[-1]['stamp'],
    first_observed_clearance_violation=None if first_breach is None else dict(
        stamp=first_breach['stamp'],pose=first_breach['pose'],clearance_m=first_breach['independent_clearance_m']),
    first_uncertified_raw_zero_s=None if not refusals else refusals[0]['stamp'],
    original_and_replacement_comparisons=len(comparisons),
    replacement_accepted_legacy_refused=len(benefit),
    first_replacement_accepted_legacy_refused=None if not benefit else benefit[0],
    replacement_refused_legacy_accepted=len(stronger),
    empirical_error_max_m=report['diagnostic_empirical_error_max_m'],
    empirical_error_samples=report['diagnostic_error_samples'],
    held_out_trials_run=0,qualified_future_uncertainty_bound=False,
    production_adoption_supported=False)
out=root/'.scratch/simulation-reliability/delayed_control_review_terminal_replacement_summary_20261007.json'
assert not out.exists()
out.write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='failure'},indent=2))
