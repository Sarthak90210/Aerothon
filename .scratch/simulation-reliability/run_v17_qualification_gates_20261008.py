"""Run one native stack at a time after exact-source targeted/offline checks."""
import json
import subprocess
import time
from pathlib import Path
root=Path(__file__).resolve().parents[2]
base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v17_source_20261008'
def wait_json(path):
    while True:
        if path.exists():
            try:return json.loads(path.read_text())
            except ValueError:pass
        time.sleep(2)
targeted=wait_json(root/'logs/reliability_reduced_v17_targeted_20261008/report.json')
if targeted.get('pass_navigation') is not True:raise SystemExit('Targeted V17 cases failed; native acceptance not started')
subprocess.run(['python3',str(base/'close_reduced_v17_targeted_20261008.py')],check=True,cwd=root)
print('Five exact-source V17 navigation cases closed PASS',flush=True)
offline=wait_json(source/'full_offline_closed_review.json')
assert offline['all_offline_checks_pass'] and offline['source_unchanged']
print('Final offline suite PASS; starting native split acceptance',flush=True)
subprocess.run(['bash',str(base/'run_reduced_v17_split_render_20261008.sh')],check=True,cwd=root)
subprocess.run(['bash',str(base/'run_reduced_v17_remaining_rendered_20261008.sh')],check=True,cwd=root)
print('Five native acceptances closed PASS; starting reduced campaign',flush=True)
watch=subprocess.Popen(['bash',str(base/'watch_v17_campaign_failed_trials_20261008.sh')],cwd=root)
try:
    subprocess.run(['bash',str(base/'run_reduced_v17_campaign_20261008.sh')],check=True,cwd=root)
finally:
    if watch.poll() is None:watch.terminate()
    watch.wait(timeout=30)
print('Campaign closed; consolidated completion review still required',flush=True)
