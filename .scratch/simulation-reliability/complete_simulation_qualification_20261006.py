"""Continue the explicitly requested simulation qualification after the seed pair.

This is one immediate task-owned job. A failed gust diagnostic closes the job
before broader qualification. No production code, thresholds or fixtures change.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'logs/reliability_remaining_qualification_20261006'
PAIR_JOB = ROOT / 'logs/reliability_standard_pair_continuation_owned_20261006'
FIRST = ROOT / 'logs/reliability_render_my_world_s20261003_handover_guard_20261006'
SECOND = ROOT / 'logs/reliability_render_my_world_s1001_handover_guard_20261006'


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    temporary = path.with_suffix(path.suffix + '.writing')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(path)


def checked_sources():
    spec = importlib.util.spec_from_file_location(
        'standard_pair_qualification', Path(__file__).with_name('continue_standard_pair_20261006.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.qualify(FIRST, 20261003)
    module.qualify(SECOND, 1001)
    if read(FIRST / 'source_manifest.json') != read(SECOND / 'source_manifest.json'):
        raise RuntimeError('Standard seed source manifests differ')


def run(command, output):
    print('Starting ' + ' '.join(map(str, command)), flush=True)
    with output.open('xb') as stream:
        completed = subprocess.run(list(map(str, command)), cwd=ROOT,
                                   stdout=stream, stderr=subprocess.STDOUT)
    print('Closed ' + output.name + ' with exit ' + str(completed.returncode), flush=True)
    return completed.returncode


def main():
    OUT.mkdir(exist_ok=False)
    coordinator_source = Path(__file__).read_bytes()
    (OUT / Path(__file__).name).write_bytes(coordinator_source)
    report = dict(state='WAITING_FOR_STANDARD_PAIR_AND_OFFLINE_SUITE',
                  coordinator_sha256=hashlib.sha256(coordinator_source).hexdigest(),
                  source_changed=False, gust_diagnostics=[], navigation=None,
                  rendered=[], hardware_qualified=False, flights_qualified=False)
    write(OUT / 'report.json', report)
    while True:
        status = read(PAIR_JOB / 'status.json')
        if status['state'] != 'RUNNING':
            break
        time.sleep(5)
    if status['state'] != 'COMPLETED' or status.get('exit_code') != 0:
        raise RuntimeError('Seed pair/offline suite did not close successfully')
    pair = read(ROOT / 'logs/reliability_standard_pair_handover_guard_20261006.json')
    if not (pair.get('both_full_acceptances_passed') is True
            and pair.get('full_offline_suite_exit_code') == 0
            and pair.get('source_unchanged') is True):
        raise RuntimeError('Missing verified current-source acceptance and offline suite')
    checked_sources()
    report['state'] = 'RUNNING_GUST_AND_DELAY_DIAGNOSTICS'
    report['qualified_standard_pair'] = pair
    write(OUT / 'report.json', report)
    # Include the saved dirty seed 0 and late seed 1 failures, plus seeds 1-5.
    # Each fixture executes the production controller with actual command delay.
    for seed in range(6):
        for kind in ('dirty', 'late'):
            checked_sources()
            stem = f'gust_{kind}_s{seed}_delay040'
            output = OUT / (stem + '.json')
            code = run(['/usr/bin/bash', '.scratch/simulation-reliability/check_gust_probe.sh',
                        '--seed', seed, '--kind', kind, '--delay', '.4', '--out', output],
                       OUT / (stem + '.log'))
            diagnostic = read(output) if output.exists() else {}
            rows = diagnostic.get('rows', [])
            item = dict(seed=seed, kind=kind, exit_code=code,
                        passed=code == 0 and diagnostic.get('passed') is True,
                        failure=diagnostic.get('failure', 'missing diagnostic report'),
                        minimum_recorded_clearance_m=min(
                            (r['independent_clearance_m'] for r in rows), default=None),
                        output=str(output.relative_to(ROOT)))
            report['gust_diagnostics'].append(item)
            write(OUT / 'report.json', report)
    checked_sources()
    if not all(item['passed'] for item in report['gust_diagnostics']):
        report['state'] = 'GUST_AND_DELAY_DIAGNOSTICS_FAILED'
        write(OUT / 'report.json', report)
        print('Gust/delay failures preserved. Broader qualification has not started.', flush=True)
        return 1
    report['state'] = 'RUNNING_NAVIGATION_MATRIX'
    write(OUT / 'report.json', report)
    matrix = ROOT / 'logs/reliability_navigation_matrix_handover_guard_20261006'
    code = run(['/usr/bin/bash',
                '.scratch/simulation-reliability/start_qualified_navigation_matrix_20261006.sh',
                FIRST, SECOND, matrix, '6'], OUT / 'navigation_matrix.log')
    report['navigation'] = dict(exit_code=code, output=str(matrix.relative_to(ROOT)),
                               report=read(matrix / 'report.json') if (matrix / 'report.json').exists() else None)
    checked_sources()
    # Preserve every rendered result even if a navigation trial failed.
    # Rendered stacks remain sequential, with the standard full 22-check grader.
    report['state'] = 'RUNNING_ADDITIONAL_RENDERED_ACCEPTANCE'
    write(OUT / 'report.json', report)
    for world in ('shipped', 'rb_rotated', 'split_corridors'):
        checked_sources()
        output = ROOT / f'logs/reliability_render_{world}_s20261003_handover_guard_20261006'
        env = dict(os.environ, AEROTHON_RENDER_TRIAL='mission')
        env.pop('AEROTHON_CORRIDOR_ENTRY', None)
        env.pop('AEROTHON_CORRIDOR_HANDOVER', None)
        with (OUT / f'rendered_{world}.log').open('xb') as stream:
            result = subprocess.run(['/usr/bin/bash', 'scripts/run_recorded_acceptance.sh',
                f'sim/worlds/{world}.json', '20261003', str(output),
                'logs/delivery_profile_20261005.json'], cwd=ROOT, env=env,
                stdout=stream, stderr=subprocess.STDOUT)
        archive_code = run(['/usr/bin/python3',
            '.scratch/simulation-reliability/archive_recorded_source.py', output],
            OUT / f'rendered_{world}_archive.log') if output.exists() else None
        summary = read(output / 'summary.json') if (output / 'summary.json').exists() else None
        report['rendered'].append(dict(world=world, seed=20261003,
            exit_code=result.returncode, archive_exit_code=archive_code,
            output=str(output.relative_to(ROOT)), summary=summary))
        write(OUT / 'report.json', report)
    checked_sources()
    matrix_pass = report['navigation']['exit_code'] == 0
    rendered_pass = all(item['exit_code'] == 0 and item['archive_exit_code'] == 0
                        and item['summary'] and item['summary'].get('acceptance_pass') is True
                        for item in report['rendered'])
    report['state'] = 'SIMULATION_QUALIFICATION_PASSED' if matrix_pass and rendered_pass else 'SIMULATION_QUALIFICATION_FAILED'
    write(OUT / 'report.json', report)
    return 0 if matrix_pass and rendered_pass else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        report_path = OUT / 'report.json'
        if report_path.exists():
            report = read(report_path)
            report.update(state='QUALIFICATION_COORDINATOR_ERROR', error=repr(error))
            write(report_path, report)
        raise
