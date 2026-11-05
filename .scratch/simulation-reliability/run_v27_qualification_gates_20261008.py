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
wait_json(root/'logs/reliability_reduced_v26_targeted_20261008/my_world_field_s3/navigation_grade.json')
print('V26 domain 41 trial closed; V27 can use it while domain 40 waits for the prior batch to close',flush=True)
watch=subprocess.Popen(['bash',str(base/'watch_v27_failed_trials_20261008.sh')],cwd=root)
try:subprocess.run(['bash',str(base/'probe_reduced_targeted_v27_20261008.sh')],check=True,cwd=root)
finally:
    if watch.poll() is None:watch.terminate()
    watch.wait(timeout=30)
subprocess.run(['python3',str(base/'close_reduced_v27_targeted_20261008.py')],check=True,cwd=root)
print('Five exact-source V27 navigation cases PASS; starting one full offline suite',flush=True)
subprocess.run(['bash',str(base/'run_reduced_v27_full_offline_20261008.sh')],check=True,cwd=root)
watch=subprocess.Popen(['bash',str(base/'watch_v27_native_failed_trials_20261008.sh')],cwd=root)
try:
    print('Final offline suite PASS; starting native split acceptance',flush=True)
    subprocess.run(['bash',str(base/'run_reduced_v27_split_render_20261008.sh')],check=True,cwd=root)
    subprocess.run(['bash',str(base/'run_reduced_v27_remaining_rendered_20261008.sh')],check=True,cwd=root)
finally:
    if watch.poll() is None:watch.terminate()
    watch.wait(timeout=30)
print('Five native acceptances PASS; starting reduced two-worker campaign',flush=True)
watch=subprocess.Popen(['bash',str(base/'watch_v27_campaign_failed_trials_20261008.sh')],cwd=root)
try:subprocess.run(['bash',str(base/'run_reduced_v27_campaign_20261008.sh')],check=True,cwd=root)
finally:
    if watch.poll() is None:watch.terminate()
    watch.wait(timeout=30)
print('Campaign closed; consolidated completion review still required',flush=True)
