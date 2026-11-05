"""Preserve rejected prototype bytes, then retain the existing pose fallback."""
import hashlib, json, shutil
from pathlib import Path
root = Path(__file__).resolve().parents[2]
snapshot = root / '.scratch/braked_navigation_candidate_20261007'
controller = snapshot / 'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
closed = root / 'logs/reliability_live_clock_regression_rejection_20261007'
closed.mkdir(exist_ok=False)
shutil.copy2(controller, closed / 'velocity_controller.py')
shutil.copy2(root / 'logs/reliability_live_clock_controller_regressions_20261007.log', closed / 'regressions.log')
source = controller.read_text()
old = "                not self._velocity_fresh()):"
assert source.count(old) == 1
source = source.replace(old, "                self._velocity_fault or (self._fcu_velocity_t is not None and not self._velocity_fresh())):")
old = "                sample_epoch = min(self._pose_t, self._fcu_velocity_t)"
assert source.count(old) == 1
source = source.replace(old,
    "                # Preserve the supported FCU-pose finite-difference fallback.\n"
    "                # Once an EKF velocity stream exists, stale captures still stop.\n"
    "                sample_epoch = min(self._pose_t, self._fcu_velocity_t) if self._fcu_velocity_t is not None else self._pose_t")
controller.write_text(source)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(closed / 'closure.json').write_text(json.dumps(dict(
    result='4 failed, 25 passed', adopted=False,
    cause='New post-planning check accidentally removed the existing pose-based velocity fallback.',
    rejected_controller_sha256=sha(closed / 'velocity_controller.py'),
    regression_log_sha256=sha(closed / 'regressions.log'),
    production_modified=False), indent=2)+'\n')
path = snapshot / 'candidate_provenance.json'
record = json.loads(path.read_text())
for name in record['modified']:
    record['modified'][name] = sha(snapshot/name)
record['corrections'] = [
    'Forecast reads command-delay parameter before the inner local assignment.',
    'Retain existing pose-derived velocity fallback; reject stale or invalid actual EKF streams.']
path.write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(dict(controller_sha256=sha(controller), rejected_source_preserved=str(closed))))
