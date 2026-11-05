"""Run the V40 reduced-qualification gates in order, with their watchdogs.

The focused native return is run separately, before this driver, because it is
the gate the V39 pipeline died on. Start this only once that stage has written
its own closed review.

    python3 .scratch/simulation-reliability/run_v40_qualification_gates_20261010.py
"""
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
base = root/'.scratch/simulation-reliability'
FOCUSED = root/'logs/reliability_reduced_v40_focused_split_s20261003_20261010'


def stage(*command, watchdog=None):
    watch = subprocess.Popen(['bash', str(base/watchdog)], cwd=root) if watchdog else None
    try:
        subprocess.run(command, check=True, cwd=root)
    finally:
        if watch is not None:
            if watch.poll() is None:
                watch.terminate()
            watch.wait(timeout=30)


review = json.loads((FOCUSED/'focused_source_closed_review.json').read_text())
assert review['focused_return_pass'] and review['aircraft_contact_evidence']['contact_free']
print('Focused native return closed on V40; starting the five targeted navigation cases', flush=True)

stage('bash', str(base/'probe_reduced_targeted_v40_20261010.sh'),
      watchdog='watch_v40_failed_trials_20261010.sh')
stage('python3', str(base/'close_reduced_v40_targeted_20261010.py'))
print('Five targeted navigation cases PASS; running one complete reduced offline suite', flush=True)

stage('bash', str(base/'run_reduced_v40_full_offline_20261010.sh'))
print('Reduced offline suite PASS; starting the five full rendered acceptances', flush=True)

try:
    stage('bash', str(base/'run_reduced_v40_split_render_20261010.sh'),
          watchdog='watch_v40_native_failed_trials_20261010.sh')
    stage('bash', str(base/'run_reduced_v40_remaining_rendered_20261010.sh'),
          watchdog='watch_v40_native_failed_trials_20261010.sh')
finally:
    pass
print('Five native acceptances PASS; starting the 96-flight reduced campaign', flush=True)

stage('bash', str(base/'run_reduced_v40_campaign_20261010.sh'),
      watchdog='watch_v40_campaign_failed_trials_20261010.sh')
print('Campaign closed; checking every source, case, exclusion and artifact', flush=True)

stage('python3', str(base/'close_reduced_v40_qualification_20261010.py'))
print('Reduced qualification verified and consolidated report closed', flush=True)
sys.exit(0)
