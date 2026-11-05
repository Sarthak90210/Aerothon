"""Exercise coordinator failure gates without launching any flight or test batch."""
import importlib.util
import json
from pathlib import Path
import tempfile


def exercise(name, status, pair, source_error, expected):
    path = Path(__file__).with_name('complete_simulation_qualification_20261006.py')
    spec = importlib.util.spec_from_file_location('completion_gate_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='aerothon_completion_gate_') as directory:
        root = Path(directory)
        module.ROOT = root
        module.OUT = root / 'result'
        module.PAIR_JOB = root / 'pair_job'
        module.PAIR_JOB.mkdir()
        (module.PAIR_JOB / 'status.json').write_text(json.dumps(status))
        (root / 'logs').mkdir()
        if pair is not None:
            (root / 'logs/reliability_standard_pair_handover_guard_20261006.json').write_text(json.dumps(pair))

        def checked():
            if source_error:
                raise RuntimeError(source_error)

        def forbidden(*args):
            raise AssertionError('An unqualified command was launched')

        module.checked_sources = checked
        module.run = forbidden
        module.subprocess.run = forbidden
        try:
            module.main()
        except RuntimeError as error:
            assert expected in str(error), str(error)
        else:
            raise AssertionError('Failure gate accepted ' + name)
        assert not list(module.OUT.glob('gust_*'))
        print('PASS ' + name)


exercise('failed seed or offline job', {'state': 'FAILED', 'exit_code': 1},
         None, None, 'did not close successfully')
exercise('unqualified pair report', {'state': 'COMPLETED', 'exit_code': 0},
         {'both_full_acceptances_passed': False, 'full_offline_suite_exit_code': 0,
          'source_unchanged': True}, None, 'Missing verified')
exercise('changed qualified source', {'state': 'COMPLETED', 'exit_code': 0},
         {'both_full_acceptances_passed': True, 'full_offline_suite_exit_code': 0,
          'source_unchanged': True}, 'Source changed after qualification', 'Source changed')
