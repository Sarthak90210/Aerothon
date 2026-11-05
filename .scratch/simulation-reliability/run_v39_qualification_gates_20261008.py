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
wait_json(root/'logs/reliability_reduced_v38_targeted_20261008/report.json')
print('V38 targeted trials safely closed; V39 reuses domains 40 and 41',flush=True)
watch=subprocess.Popen(['bash',str(base/'watch_v39_failed_trials_20261008.sh')],cwd=root)
try:subprocess.run(['bash',str(base/'probe_reduced_targeted_v39_20261008.sh')],check=True,cwd=root)
finally:
    if watch.poll() is None:watch.terminate()
    watch.wait(timeout=30)
subprocess.run(['python3',str(base/'close_reduced_v39_targeted_20261008.py')],check=True,cwd=root)
print('Five exact-source V39 navigation cases PASS; starting one complete reduced-scope offline suite',flush=True)
print('Targeted navigation PASS; running short native return regression before the full offline suite',flush=True)
subprocess.run(['bash',str(base/'run_reduced_v39_focused_split_20261009.sh')],check=True,cwd=root)
subprocess.run(['bash',str(base/'run_reduced_v39_full_offline_20261008.sh')],check=True,cwd=root)
watch=subprocess.Popen(['bash',str(base/'watch_v39_native_failed_trials_20261008.sh')],cwd=root)
try:
    print('Reduced-scope offline suite PASS; starting native split acceptance',flush=True)
    subprocess.run(['bash',str(base/'run_reduced_v39_split_render_20261008.sh')],check=True,cwd=root)
    subprocess.run(['bash',str(base/'run_reduced_v39_remaining_rendered_20261008.sh')],check=True,cwd=root)
finally:
    if watch.poll() is None:watch.terminate()
    watch.wait(timeout=30)
print('Five native acceptances PASS; starting reduced two-worker campaign',flush=True)
watch=subprocess.Popen(['bash',str(base/'watch_v39_campaign_failed_trials_20261008.sh')],cwd=root)
try:subprocess.run(['bash',str(base/'run_reduced_v39_campaign_20261008.sh')],check=True,cwd=root)
finally:
    if watch.poll() is None:watch.terminate()
    watch.wait(timeout=30)
print('Campaign closed; checking every source, configuration, exclusion and artifact before completion',flush=True)
subprocess.run(['python3',str(base/'close_reduced_v39_qualification_20261008.py')],check=True,cwd=root)
print('Reduced qualification verified and consolidated report closed',flush=True)
