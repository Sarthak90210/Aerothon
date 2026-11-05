"""Run requested full rendered courses sequentially after frozen matrix closes.

This characterizes the passing standard-pair source. Coupled gust qualification
remains a separate open failure, regardless of these rendered results.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'logs/reliability_baseline_rendered_courses_20261006'
MATRIX = ROOT / 'logs/reliability_navigation_baseline_matrix_assets_20261006'
MATRIX_JOB = ROOT / 'logs/reliability_navigation_baseline_matrix_assets_owned_20261006'
FIRST = ROOT / 'logs/reliability_render_my_world_s20261003_handover_guard_20261006'


def read(path):
    return json.loads(path.read_text())


def write(report):
    temporary = OUT / 'report.json.writing'
    temporary.write_text(json.dumps(report, indent=2) + '\n')
    temporary.replace(OUT / 'report.json')


def unchanged():
    for manifest in ('source_manifest.json', 'qualification_tools_manifest.json'):
        for name, expected in read(FIRST / manifest).items():
            path = Path(name)
            if not path.is_absolute():
                path = ROOT / path
            assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'Source changed: ' + name


def freeze_visual_assets(output):
    destination = output / 'runtime_visual_assets'
    destination.mkdir(exist_ok=False)
    manifest = {}
    for path in sorted(Path('/tmp/aerothon_m2_assets').glob('*')):
        if path.is_file():
            data = path.read_bytes()
            (destination / path.name).write_bytes(data)
            manifest[path.name] = hashlib.sha256(data).hexdigest()
    assert 'qr_payloads.txt' in manifest and 'qr_matrices.json' in manifest
    (output / 'runtime_visual_assets_manifest.json').write_text(json.dumps(dict(
        collected_wall=time.time(), source='/tmp/aerothon_m2_assets', sha256=manifest,
        provenance='Owned rendered runtime, captured after readiness before the next stack'), indent=2)+'\n')


def main():
    OUT.mkdir(exist_ok=False)
    data = Path(__file__).read_bytes()
    (OUT / Path(__file__).name).write_bytes(data)
    report = dict(state='WAITING_FOR_BASELINE_MATRIX_CLOSURE',
        coordinator_sha256=hashlib.sha256(data).hexdigest(), baseline_only=True,
        coupled_gust_and_delay_qualified=False, source_changed=False, rendered=[],
        hardware_qualified=False, flights_qualified=False)
    write(report)
    while read(MATRIX_JOB / 'status.json')['state'] == 'RUNNING':
        time.sleep(5)
    assert (MATRIX / 'report.json').exists(), 'Navigation matrix did not finish its full report'
    report['navigation'] = read(MATRIX / 'report.json')
    assert report['navigation'].get('source_unchanged') is True
    unchanged()
    report['state'] = 'RUNNING_BASELINE_RENDERED_COURSES'
    write(report)
    for world in ('shipped', 'rb_rotated', 'split_corridors'):
        unchanged()
        output = ROOT / f'logs/reliability_render_{world}_s20261003_baseline_20261006'
        env = dict(os.environ, AEROTHON_RENDER_TRIAL='mission')
        env.pop('AEROTHON_CORRIDOR_ENTRY', None)
        env.pop('AEROTHON_CORRIDOR_HANDOVER', None)
        print('Starting full rendered '+world+' seed20261003', flush=True)
        captured = False
        with (OUT / f'{world}.log').open('xb') as stream:
            process = subprocess.Popen(['/usr/bin/bash', 'scripts/run_recorded_acceptance.sh',
                f'sim/worlds/{world}.json', '20261003', str(output),
                'logs/delivery_profile_20261005.json'], cwd=ROOT, env=env,
                stdout=stream, stderr=subprocess.STDOUT)
            while process.poll() is None:
                if not captured and (output / 'runtime_configuration_manifest.json').exists():
                    freeze_visual_assets(output)
                    captured = True
                time.sleep(2)
            code = process.wait()
        with (OUT / f'{world}_archive.log').open('xb') as stream:
            archive = subprocess.run(['/usr/bin/python3',
                '.scratch/simulation-reliability/archive_recorded_source.py', str(output)],
                cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT) if output.exists() else None
        summary = read(output / 'summary.json') if (output / 'summary.json').exists() else None
        report['rendered'].append(dict(world=world, seed=20261003, exit_code=code,
            archive_exit_code=archive.returncode if archive else None,
            runtime_visual_assets_captured=captured,
            output=str(output.relative_to(ROOT)), summary=summary))
        write(report)
        unchanged()
        print('Closed '+world+' with exit '+str(code), flush=True)
    passed = all(item['exit_code']==0 and item['archive_exit_code']==0 and
        item['runtime_visual_assets_captured'] and item['summary'] and
        item['summary'].get('acceptance_pass') is True for item in report['rendered'])
    report['state'] = 'BASELINE_RENDERED_COURSES_PASSED' if passed else 'BASELINE_RENDERED_COURSES_FAILED'
    write(report)
    return 0 if passed else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        if (OUT / 'report.json').exists():
            report = read(OUT / 'report.json')
            report.update(state='BASELINE_COORDINATOR_ERROR', error=repr(error))
            write(report)
        raise
