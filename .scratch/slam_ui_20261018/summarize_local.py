"""Keep an evidence index for the local SITL continuation, without pass inflation."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
db = sqlite3.connect(HERE/'local_sitl_state/commands.sqlite')
commands = []
for cid, request, result in db.execute('SELECT id,request,result FROM commands ORDER BY rowid'):
    req, res = json.loads(request), json.loads(result)
    entry = {'command_id':cid, 'request':req, 'result':res}
    if res.get('reason') == 'operator stopped test':
        entry['interpretation'] = 'operator-interrupted; Completed confirms recovery/disarm, not task completion'
    commands.append(entry)
db.close()
snapshots = []
for path in sorted(HERE.glob('local_*_*.json')):
    data = json.loads(path.read_text())
    if 'latest' not in data:
        continue
    latest, history = data['latest'], data.get('history', [])
    snapshots.append({'path':str(path.relative_to(ROOT)), 'telemetry_messages':len(history),
        'fcu_connected_messages':sum(h.get('safety',{}).get('fcu_connected') is True for h in history),
        'map_messages':len(data.get('maps',[])), 'final_execution':latest.get('execution'),
        'final_mission':latest.get('mission'), 'final_flight':latest.get('flight'),
        'final_devices':latest.get('devices'), 'final_winch':latest.get('winch')})
    snapshots[-1]['command_outcome'] = data.get('command_outcome')
sources = ['src/aerothon_payload/winch_ctrl/winch_ctrl/winch_node.py',
           'src/aerothon_runtime/aerothon_runtime/execution_node.py',
           'sim/test_winch.py', 'sim/test_gcs_merge_contract.py']
value = {'scope':'Continue original GCS Testing options locally using actual ArduCopter SITL, Gazebo, production runtime and local gateway. No Pi or physical hardware accessed.',
    'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
    'fixes':[
        {'problem':'A refused ground release stayed latched during safe stop/stow and blocked readiness.',
         'change':'A replacement lower/stow/stop command clears the superseded release-refusal diagnostic; all physical release preconditions remain.'},
        {'problem':'A release during an encoder/backend fault relabeled the genuine fault as transient and later cleared it.',
         'change':'Release preserves an existing backend/encoder fault. Tests assert stop/stow also retain genuine faults.'},
        {'problem':'Completed bench tasks displayed the previous execution failure reason.',
         'change':'Successful passive/mechanism receipts have an empty reason; failed and unconfirmed-release reasons remain.'}],
    'regression':{'initial_reproduction':'3 failed, 1 passed for refused-release stop/stow and true fault preservation before fix',
        'receipt_reproduction':'1 failed before receipt fix',
        'affected':'51 passed in20.19s; sim/test_winch.py, test_winch_gpio.py, test_remote_device_link.py, test_gcs_merge_contract.py',
        'log':str((HERE/'local_backend_tests.log').relative_to(ROOT))},
    'setup':{'camera':'640x360 rendered by Gazebo; measured17-18Hz vehicle time against10Hz requirement',
        'lidar':'measured10Hz vehicle time against8Hz requirement',
        'profile':'local_sitl_state/profiles.json', 'venue':'local_sitl_venue.yaml',
        'constraints':'No threshold changed. Test venue supplies measured camera dimensions and shipped SITL WINCH_RATE_MAX1.0. Early inconsistent-resolution mission attempt was operator-interrupted and remains separate.'},
    'known_issues':[
        'Avoidance route armed and reached3m but made under1m progress toward local(14,0)/(20,0) in112s; production Stop recovered/disarmed. Navigation algorithms unchanged.',
        'Gateway actuator capability flags intermittently not-ok caused known Failed starts even when the operator snapshot appeared good. No capability gate bypassed.',
        'Full mission reached decoded start QR and AlignToBanner, then remained in banner surface fitting/relocation at300s. Operator-interrupted and recovered/disarmed, not a completed or accepted mission.',
        'Delivery GPS5m: actual3m marker could not fit the camera vertical field at that selected height. Setup-limited attempt, operator-stopped; not classified as runtime defect.',
        'Delivery GPS7m retry: refused before arming because camera/winch actuator feedback capability flags were not-ok. Successful feasible-altitude GPS delivery remains pending.',
        'Delivery here: reached WinchDrop; production automatically raised tracking to6.76m for the configured3m pad and selected5.5m release height. It then reported payload not confirmed: load calibration missing or unqualified. No delivery success claimed.',
        'Final Stop arrived during Delivery-here failure recovery, so a terminal Completed/operator-stopped receipt must not hide the earlier calibration failure in runtime.log.',
        'A large host wall-clock gap appears between recorded events on18 and19October. Interrupted/paused intervals are retained; none of these attempts is qualification evidence.',
        'Mechanism lower and manual transmitter flight were not freshly completed; transmitter RC mapping is unconfigured. Prior-context options remain prior evidence, not fresh passes.'],
    'commands':commands, 'snapshots':snapshots,
    'status':'local SITL continuation stopping for final software regression; recovery/disarm and owned-process shutdown pending'}
shutdown = HERE/'local_shutdown.json'
if shutdown.exists():
    value['shutdown'] = json.loads(shutdown.read_text())
    value['status'] = 'Local continuation finished with explicit pending outcomes; recorded disarm and owned runtime/simulator shutdown complete. No Pi access or deployment.'
target = HERE/'local_testing.json'
target.write_text(json.dumps(value,indent=2))
print(json.dumps({'receipt':str(target),'commands':len(commands),'snapshots':len(snapshots)}))
