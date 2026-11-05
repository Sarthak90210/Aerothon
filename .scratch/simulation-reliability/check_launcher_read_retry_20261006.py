"""Reproduce a transient status-file replacement gap at the actual read seam."""
import importlib.util
import json
from pathlib import Path

path = Path(__file__).with_name('launch_owned_job_20261006.py')
spec = importlib.util.spec_from_file_location('owned_launcher_read_test', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.time.sleep = lambda seconds: None


class ReplacedStatus:
    def __init__(self, errors):
        self.errors = list(errors)
        self.calls = 0

    def read_text(self):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return '{"state":"RUNNING"}'


status = ReplacedStatus([FileNotFoundError('status replacement gap')])
assert module.read_json(status) == {'state': 'RUNNING'}
assert status.calls == 2
status = ReplacedStatus([json.JSONDecodeError('transient empty status', '', 0)])
assert module.read_json(status) == {'state': 'RUNNING'}
assert status.calls == 2
status = ReplacedStatus([OSError(61, 'No data available during replacement')])
assert module.read_json(status) == {'state': 'RUNNING'}
assert status.calls == 2
status = ReplacedStatus([FileNotFoundError('persistently missing')] * 100)
try:
    module.read_json(status)
except FileNotFoundError:
    assert status.calls > 1 and status.calls <= 30
else:
    raise AssertionError('A persistently missing status must remain an error')
status = ReplacedStatus([PermissionError(13, 'Permission denied')])
try:
    module.read_json(status)
except PermissionError:
    assert status.calls == 1
else:
    raise AssertionError('Permission errors must remain immediate errors')
print('PASS replacement gap, empty parse, ENODATA, bounded failure, permission failure')
