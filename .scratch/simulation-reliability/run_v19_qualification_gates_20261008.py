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
wait_json(root/'logs/reliability_reduced_v18_targeted_20261008/report.json')
print('V18 focused trials closed; starting V19 exact-source targeted cases',flush=True)
watch=subprocess.Popen(['bash',str(base/'watch_v19_failed_trials_20261008.sh')],cwd=root)
try:subprocess.run(['bash',str(base/'probe_reduced_targeted_v19_20261008.sh')],check=True,cwd=root)
finally:
    if watch.poll() is None:watch.terminate()
    watch.wait(timeout=30)
subprocess.run(['python3',str(base/'close_reduced_v19_targeted_20261008.py')],check=True,cwd=root)
print('Five exact-source V19 navigation cases PASS; starting one full offline suite',flush=True)
subprocess.run(['bash',str(base/'run_reduced_v19_full_offline_20261008.sh')],check=True,cwd=root)
watch=subprocess.Popen(['bash',str(base/'watch_v19_native_failed_trials_20261008.sh')],cwd=root)
try:
    print('Final offline suite PASS; starting native split acceptance',flush=True)
    subprocess.run(['bash',str(base/'run_reduced_v19_split_render_20261008.sh')],check=True,cwd=root)
    subprocess.run(['bash',str(base/'run_reduced_v19_remaining_rendered_20261008.sh')],check=True,cwd=root)
finally:
    if watch.poll() is None:watch.terminate()
    watch.wait(timeout=30)
print('Five native acceptances PASS; starting reduced two-worker campaign',flush=True)
watch=subprocess.Popen(['bash',str(base/'watch_v19_campaign_failed_trials_20261008.sh')],cwd=root)
try:subprocess.run(['bash',str(base/'run_reduced_v19_campaign_20261008.sh')],check=True,cwd=root)
finally:
    if watch.poll() is None:watch.terminate()
    watch.wait(timeout=30)
print('Campaign closed; consolidated completion review still required',flush=True)
