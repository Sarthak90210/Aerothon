"""Only a closed isolated candidate receives the compiled graph and timing log."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
status=json.loads((root/'logs/reliability_braked_navigation_candidate_restore_config_owned_20261007/status.json').read_text())
assert status['state']=='FAILED' and status['exit_code']==1
snapshot=root/'.scratch/braked_navigation_candidate_20261007'
package=snapshot/'src/aerothon_avoidance/avoidance/avoidance'
candidate=Path(__file__).with_name('fast_connected_planner_candidate_20261007.py')
(package/'fast_connected_planner_candidate.py').write_bytes(candidate.read_bytes())
controller=package/'velocity_controller.py'
source=controller.read_text()
needle='from avoidance.local_planner import LocalPlanner'
assert source.count(needle)==1
controller.write_text(source.replace(needle,
    'from avoidance.fast_connected_planner_candidate import FastConnectedPlanner as LocalPlanner'))
world=snapshot/'sim/headless_world.py'
source=world.read_text()
needle='        self.pending_velocity = deque(maxlen=512)'
assert source.count(needle)==1
source=source.replace(needle,needle+'\n        self.command_timing = []')
needle='                self.pending_velocity.append((self.t + self.args.vel_command_delay_s, command))'
assert source.count(needle)==1
source=source.replace(needle,
    '                self.command_timing.append(dict(callback_sim_s=self.t,\n'
    '                    transmit_header_sim_s=m.header.stamp.sec+m.header.stamp.nanosec*1e-9,\n'
    '                    callback_host_monotonic_s=time.monotonic(),\n'
    '                    physical_receipt_due_sim_s=self.t+self.args.vel_command_delay_s,\n'
    '                    command=command))\n'+needle)
needle='        (out / "layout.json").write_text(json.dumps(layout, sort_keys=True))'
assert source.count(needle)==1
source=source.replace(needle,needle+'\n        (out/"independent_command_receipt_timing.json").write_text(json.dumps(self.command_timing))')
world.write_text(source)
runner=snapshot/'sim/run_braked_navigation_probe.py'
source=runner.read_text()
needle="out=workspace/'logs/reliability_braked_navigation_candidate_restore_config_20261007'"
assert source.count(needle)==1
runner.write_text(source.replace(needle,"out=workspace/'logs/reliability_fast_planner_navigation_candidate_20261007'"))
provenance_path=snapshot/'candidate_provenance.json'
provenance=json.loads(provenance_path.read_text())
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
provenance['modified'].update({str(path.relative_to(snapshot)):sha(path) for path in (
    package/'fast_connected_planner_candidate.py',controller,world,runner)})
provenance.update(planner_candidate_sha256=sha(candidate),
    fixture_changed='separate command callback timing evidence only; physical motion unchanged')
provenance_path.write_text(json.dumps(provenance,indent=2)+'\n')
print(json.dumps(provenance))
