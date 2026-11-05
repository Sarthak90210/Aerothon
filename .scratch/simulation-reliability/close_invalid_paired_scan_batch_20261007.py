"""Close only escaped child groups of the rejected forecast-path batch."""
import importlib.util,json,os,signal,time
from pathlib import Path

root=Path(__file__).resolve().parents[2]
job=root/'logs/reliability_focused_paired_scan_navigation_owned_20261007'
batch=root/'logs/reliability_focused_paired_scan_navigation_20261007'
snapshot=(root/'.scratch/paired_scan_motion_candidate_20261007').resolve()
spec=importlib.util.spec_from_file_location('owned',Path(__file__).with_name('launch_owned_job_20261006.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
status=json.loads((job/'status.json').read_text())
assert status['state']=='STOPPED'
assert not module.same_process(status['command_process'])
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==status['command_process']['boot_id']
owned=[]
for path in Path('/proc').iterdir():
    if not path.name.isdigit():continue
    try:
        if (path/'cwd').resolve()!=snapshot:continue
        env=(path/'environ').read_bytes().split(b'\0')
        domain=next((int(item.split(b'=',1)[1]) for item in env if item.startswith(b'ROS_DOMAIN_ID=')),None)
        if domain is None or not 180<=domain<=189:continue
        cmd=(path/'cmdline').read_bytes().replace(b'\0',b' ').decode()
        if not (str(snapshot) in cmd or any('from '+name+' import main; main()' in cmd for name in
            ('sim.navigation_mission','camera_ctrl.camera_ctrl_node','winch_ctrl.winch_node','avoidance.velocity_controller'))):
            raise RuntimeError('Unexpected command in owned run domain: '+cmd)
        identity=module.identity(int(path.name))
        assert identity['start_ticks']>=status['command_process']['start_ticks']
        assert identity['pid']==identity['pgid']
        owned.append(dict(identity=identity,domain=domain,command=cmd))
    except (FileNotFoundError,ProcessLookupError,PermissionError):continue
for entry in owned:
    if module.same_process(entry['identity']):os.killpg(entry['identity']['pgid'],signal.SIGINT)
time.sleep(2)
for entry in owned:
    if module.same_process(entry['identity']):os.killpg(entry['identity']['pgid'],signal.SIGKILL)
review=dict(qualification_valid=False,reason='Controller initialization failed: missing AEROTHON_MOTION_FORECAST_OUT',
    observed_batch_records=json.loads((batch/'report.json').read_text())['results'],
    owned_escaped_child_groups_closed=owned,scope='Preserved invalid harness; no flight qualification')
(batch/'interruption_review.json').write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps(dict(qualification_valid=False,scoped_groups=len(owned))))
