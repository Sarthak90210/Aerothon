"""Keep normal timing: focused flights, offline, native, then two-worker matrix."""
import json,subprocess,time
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
def wait_json(path):
    while True:
        if path.exists():
            try:return json.loads(path.read_text())
            except ValueError:pass
        time.sleep(2)
wait_json(root/'logs/reliability_reduced_v27_targeted_20261008/report.json')
print('V27 targeted trials safely closed; V28 reuses domains 40 and 41',flush=True)
watch=subprocess.Popen(['bash',str(base/'watch_v28_failed_trials_20261008.sh')],cwd=root)
try:subprocess.run(['bash',str(base/'probe_reduced_targeted_v28_20261008.sh')],check=True,cwd=root)
finally:
    if watch.poll() is None:watch.terminate()
    watch.wait(timeout=30)
subprocess.run(['python3',str(base/'close_reduced_v28_targeted_20261008.py')],check=True,cwd=root)
print('Five exact-source V28 navigation cases PASS; starting one full offline suite',flush=True)
subprocess.run(['bash',str(base/'run_reduced_v28_full_offline_20261008.sh')],check=True,cwd=root)
watch=subprocess.Popen(['bash',str(base/'watch_v28_native_failed_trials_20261008.sh')],cwd=root)
try:
    print('Final offline suite PASS; starting native split acceptance',flush=True)
    subprocess.run(['bash',str(base/'run_reduced_v28_split_render_20261008.sh')],check=True,cwd=root)
    subprocess.run(['bash',str(base/'run_reduced_v28_remaining_rendered_20261008.sh')],check=True,cwd=root)
finally:
    if watch.poll() is None:watch.terminate()
    watch.wait(timeout=30)
print('Five native acceptances PASS; starting reduced two-worker campaign',flush=True)
watch=subprocess.Popen(['bash',str(base/'watch_v28_campaign_failed_trials_20261008.sh')],cwd=root)
try:subprocess.run(['bash',str(base/'run_reduced_v28_campaign_20261008.sh')],check=True,cwd=root)
finally:
    if watch.poll() is None:watch.terminate()
    watch.wait(timeout=30)
print('Campaign closed; checking every source, configuration, exclusion and artifact before completion',flush=True)
subprocess.run(['python3',str(base/'close_reduced_v28_qualification_20261008.py')],check=True,cwd=root)
print('Reduced qualification verified and consolidated report closed',flush=True)
