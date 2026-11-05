"""Forecast execution delay and reject computations that exceed their budget."""
import hashlib
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
base = root/'logs/reliability_lidar_fault_continuity_source_20261007'
provenance = json.loads((base/'candidate_provenance.json').read_text())
archive = base/'frozen_source.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == provenance['source_archive_sha256']
snapshot = root/'.scratch/command_deadline_candidate_20261007'
out = root/'logs/reliability_command_deadline_source_20261007'
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
(out/'controller.before.py').write_text(before)
after = before
replacements = {
    "        p('cruise_speed', 0.8)": "        p('cruise_speed', 0.8)\n        p('motion_computation_budget_s', 0.20)",
    '    def _publish(self, vx, vy, front, bearing, extra):': '''    def _publish(self, vx, vy, front, bearing, extra):
        computation_started = self._now()
        budget = float(self._g('motion_computation_budget_s'))
        if not math.isfinite(budget) or budget < 0:
            raise ValueError('motion computation budget must be finite and nonnegative')''',
    'receipt_turn = self._heading_at(self._now()+delay)-(self._yaw or 0.0)':
        'receipt_turn = self._heading_at(self._now()+budget+delay)-(self._yaw or 0.0)',
    "packet_wait = capture_age+float(self._g('vel_command_delay_s'))":
        "packet_wait = capture_age+budget+float(self._g('vel_command_delay_s'))",
    '        # Include holds in the delayed actuator model, including stale-data': '''        computation_elapsed = max(0.,self._now()-computation_started)
        if fresh and computation_elapsed > budget+1e-9:
            vx=vy=yaw_rate=0.0
            fresh=False
            extra['fault']='motion certificate computation deadline exceeded'
        elif fresh and (self.scan_stale() or self._pose_t is None or
                self._now()-self._pose_t > float(self._g('stale_scan_s')) or
                self._velocity_fault or (self._fcu_velocity_t is not None and not self._velocity_fresh())):
            vx=vy=yaw_rate=0.0
            fresh=False
            extra['fault']='post-certificate flight observations stale'
        extra['motion_computation_elapsed_s']=computation_elapsed
        extra['motion_computation_budget_s']=budget
        # Include holds in the delayed actuator model, including stale-data''',
}
for old, new in replacements.items():
    assert after.count(old) == 1, old
    after = after.replace(old,new)
controller.write_bytes(after.encode())
(out/'controller.candidate.py').write_bytes(controller.read_bytes())
manifest = {name:hashlib.sha256((snapshot/name).read_bytes()).hexdigest() for name in manifest}
with zipfile.ZipFile(out/'frozen_source.zip', 'x', zipfile.ZIP_DEFLATED) as handle:
    handle.writestr('source_manifest.json',json.dumps(manifest,indent=2)+'\n')
    for name in sorted(manifest):handle.writestr(name,(snapshot/name).read_bytes())
with zipfile.ZipFile(out/'frozen_source.zip') as handle:
    assert all(hashlib.sha256(handle.read(name)).hexdigest() == sha for name,sha in manifest.items())
record = dict(provenance,source_archive_sha256=hashlib.sha256((out/'frozen_source.zip').read_bytes()).hexdigest(),
    source_changes=provenance['source_changes']+['include computation budget before command receipt; reject expired certificates'],
    motion_computation_budget_s=.2, future_disturbance_bound_qualified=False)
(out/'candidate_provenance.json').write_text(json.dumps(record,indent=2)+'\n')
(snapshot/'candidate_provenance.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='asset_sha256'}))
