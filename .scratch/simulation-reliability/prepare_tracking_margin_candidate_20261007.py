"""Add routing reserve in an isolated candidate without reducing stop clearance."""
import hashlib
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
base = root/'logs/reliability_lidar_fault_continuity_source_20261007'
provenance = json.loads((base/'candidate_provenance.json').read_text())
archive = base/'frozen_source.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == provenance['source_archive_sha256']
snapshot = root/'.scratch/tracking_margin_candidate_20261007'
out = root/'logs/reliability_tracking_margin_source_20261007'
snapshot.mkdir(exist_ok=False)
out.mkdir(exist_ok=False)
with zipfile.ZipFile(archive) as handle:
    manifest = json.loads(handle.read('source_manifest.json'))
    for name, sha in manifest.items():
        data = handle.read(name)
        assert hashlib.sha256(data).hexdigest() == sha
        target = (snapshot/name).resolve()
        assert target.is_relative_to(snapshot.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
for name, sha in provenance['asset_sha256'].items():
    data = (root/'.scratch/lidar_fault_continuity_candidate_20261007'/name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == sha
    target = (snapshot/name).resolve()
    assert target.is_relative_to(snapshot.resolve())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
name = 'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
controller = snapshot/name
before = controller.read_text()
(out/'controller.before.py').write_bytes(controller.read_bytes())
old = "        p('cruise_speed', 0.8)"
assert before.count(old) == 1
after = before.replace(old, old+"\n        p('path_tracking_margin_m', 0.05)")
old = '    def _local_path(self, axis_bearing):'
assert after.count(old) == 1
replacement = '''    def _local_path(self, axis_bearing):
        # Steering paths retain extra room for measured tracking error. The
        # motion certificate and recovery still enforce the original full
        # 0.70 m clearance and 0.025 m sampling reserve; neither is reduced.
        base = self._planner
        margin = float(self._g('path_tracking_margin_m'))
        if not math.isfinite(margin) or margin < 0:
            raise ValueError('path tracking margin must be finite and nonnegative')
        guard = LocalPlanner(clearance=base.clearance+margin,
            resolution=base.resolution,lookahead=base.lookahead,
            occupied_radius=base.occupied_radius)
        for name in ('points','tree','bearings','ranges','sensor_origin'):
            setattr(guard,name,getattr(base,name))
        self._planner = guard
        try:
            return self._local_path_reserved(axis_bearing)
        finally:
            self._planner = base
            base.path,base.reason = guard.path,guard.reason

    def _local_path_reserved(self, axis_bearing):'''
after = after.replace(old, replacement)
old = '                      required_clearance_m=self._planner.clearance,'
assert after.count(old) == 1
after = after.replace(old, old+"\n                      routing_clearance_m=self._planner.clearance+float(self._g('path_tracking_margin_m')),")
controller.write_bytes(after.encode())
(out/'controller.candidate.py').write_bytes(controller.read_bytes())
manifest = {name:hashlib.sha256((snapshot/name).read_bytes()).hexdigest() for name in manifest}
with zipfile.ZipFile(out/'frozen_source.zip', 'x', zipfile.ZIP_DEFLATED) as handle:
    handle.writestr('source_manifest.json', json.dumps(manifest, indent=2)+'\n')
    for name in sorted(manifest):
        handle.writestr(name, (snapshot/name).read_bytes())
with zipfile.ZipFile(out/'frozen_source.zip') as handle:
    assert all(hashlib.sha256(handle.read(name)).hexdigest() == sha for name, sha in manifest.items())
record = dict(provenance, source_archive_sha256=hashlib.sha256((out/'frozen_source.zip').read_bytes()).hexdigest(),
    source_changes=provenance['source_changes']+['0.05 m additional steering-path tracking reserve'],
    required_clearance_m=.70,sampling_reserve_m=.025,path_tracking_margin_m=.05,
    future_disturbance_bound_qualified=False)
(out/'candidate_provenance.json').write_text(json.dumps(record, indent=2)+'\n')
(snapshot/'candidate_provenance.json').write_text(json.dumps(record, indent=2)+'\n')
here = Path(__file__).parent
checks = (here/'check_lidar_fault_continuity_regressions_20261007.py').read_text()
checks = checks.replace('.scratch/lidar_fault_continuity_candidate_20261007', '.scratch/tracking_margin_candidate_20261007')
(here/'check_tracking_margin_regressions_20261007.py').write_bytes(checks.encode())
runner = (here/'run_lidar_fault_continuity_batch_20261007.py').read_text()
for old, new in {
    '.scratch/lidar_fault_continuity_candidate_20261007': '.scratch/tracking_margin_candidate_20261007',
    'logs/reliability_lidar_fault_continuity_source_20261007': 'logs/reliability_tracking_margin_source_20261007',
    'logs/reliability_lidar_fault_continuity_navigation_20261007': 'logs/reliability_tracking_margin_navigation_20261007',
    'logs/reliability_lidar_fault_continuity_trials_retry1_owned_20261007': 'logs/reliability_tracking_margin_trials_owned_20261007',
    'ros_domain=215+i': 'ros_domain=218+i',
}.items():
    assert old in runner, old
    runner = runner.replace(old, new)
runner = runner.replace("assert '5 passed' in (qualified/'after.log').read_text()", "assert '5 passed' in (root/'logs/reliability_lidar_fault_continuity_source_20261007/after.log').read_text()")
(here/'run_tracking_margin_batch_20261007.py').write_bytes(runner.encode())
script = '''#!/usr/bin/env bash
set -eo pipefail
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=222 ROS_LOCALHOST_ONLY=1
/usr/bin/python3 .scratch/simulation-reliability/check_tracking_margin_regressions_20261007.py > logs/reliability_tracking_margin_trials_owned_20261007/regressions.log 2>&1
exec /usr/bin/python3 .scratch/simulation-reliability/run_tracking_margin_batch_20261007.py
'''
(here/'run_tracking_margin_trials_20261007.sh').write_bytes(script.encode())
print(json.dumps({k:v for k,v in record.items() if k != 'asset_sha256'}))
