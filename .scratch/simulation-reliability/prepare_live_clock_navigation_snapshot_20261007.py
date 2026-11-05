"""Isolated clock delivery and capture-age forecast; physical fixture unchanged."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
status=json.loads((root/'logs/reliability_fast_planner_navigation_candidate_owned_20261007/status.json').read_text())
assert status['state']=='FAILED' and status['exit_code']==1
snapshot=root/'.scratch/braked_navigation_candidate_20261007'
package=snapshot/'src/aerothon_avoidance/avoidance/avoidance'
helper=Path(__file__).with_name('independent_ros_clock_candidate_20261007.py')
(package/'independent_ros_clock_candidate.py').write_bytes(helper.read_bytes())
controller=package/'velocity_controller.py'
source=controller.read_text()
needle='    node = VelocityController()\n    try:'
assert source.count(needle)==1
source=source.replace(needle,
    '    node = VelocityController()\n'
    '    from avoidance.independent_ros_clock_candidate import IndependentRosClock\n'
    '    clock_driver = IndependentRosClock(node)\n    try:')
needle='    finally:\n        node.destroy_node()'
assert source.count(needle)==1
source=source.replace(needle,'    finally:\n        clock_driver.close()\n        node.destroy_node()')
needle="        fresh = 'fault' not in extra\n"
assert source.count(needle)==1
source=source.replace(needle,
    "        extra = dict(extra)\n"
    "        if 'fault' not in extra and (self.scan_stale() or\n"
    "                self._pose_t is None or self._now()-self._pose_t > float(self._g('stale_scan_s')) or\n"
    "                not self._velocity_fresh()):\n"
    "            extra['fault'] = 'post-planning flight observations stale'\n"+needle)
# Determine the method name from the actual controller source; no test-only
# freshness predicate is substituted.
assert '    def scan_stale(self):' in source
needle='            def motion_clear(command):\n'
assert source.count(needle)==1
source=source.replace(needle,needle+
    '                forecast_now = self._now()\n'
    '                sample_epoch = min(self._pose_t, self._fcu_velocity_t)\n'
    '                capture_age = max(0., forecast_now-sample_epoch)\n'
    "                packet_wait = capture_age+float(self._g('vel_command_delay_s'))\n")
needle='duration = delay+6*tau+'
assert source.count(needle)==1
source=source.replace(needle,'duration = packet_wait+6*tau+')
source=source.replace('if t<delay:','if t<packet_wait:')
source=source.replace('self._command_known(self._now()+t)','self._command_known(sample_epoch+t)')
source=source.replace('self._effective_command(self._now()+t)','self._effective_command(sample_epoch+t)')
source=source.replace('if t<delay+tau:','if t<packet_wait+tau:')
source=source.replace('if t>=delay+tau:','if t>=packet_wait+tau:')
controller.write_text(source)
runner=snapshot/'sim/run_braked_navigation_probe.py'
source=runner.read_text()
needle="out=workspace/'logs/reliability_fast_planner_navigation_candidate_20261007'"
assert source.count(needle)==1
runner.write_text(source.replace(needle,"out=workspace/'logs/reliability_live_clock_navigation_candidate_20261007'"))
path=snapshot/'candidate_provenance.json'
record=json.loads(path.read_text())
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
record['modified'].update({str(p.relative_to(snapshot)):sha(p) for p in (
    package/'independent_ros_clock_candidate.py',controller,runner)})
record.update(clock_candidate_sha256=sha(helper),
    clock_scope='actual ROS /clock callbacks; no simulator geometry or status',
    physical_response_or_delay_changed=False,
    sensor_capture_age_included_in_motion_forecast=True,
    post_planning_stale_observations_stop=True)
path.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
