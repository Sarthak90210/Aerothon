"""Freeze repaired observation/evidence source, run full checks and live courses."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'logs/reliability_banner_capture_qualification_continuity_20261007'
sys.path.insert(0,str(ROOT/'sim'))
from campaign_record import source_manifest


def read(path):return json.loads(path.read_text())


def manifest():
    source_manifest.cache_clear()
    data=source_manifest(ROOT)
    for directory in ('src','scripts','sim'):
        for path in (ROOT/directory).rglob('*'):
            if path.is_file() and path.suffix in ('.xacro','.urdf','.png','.txt','.glb') and not any(
                name in path.parts for name in ('node_modules','dist','build','__pycache__')):
                data[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ('capture_runtime_configuration.py','audit_decision_inputs.py',
                 'grade_focused_return.py','grade_focused_delivery.py'):
        path=Path(__file__).with_name(name)
        data[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    path=ROOT/'logs/delivery_profile_20261005.json'
    data[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    return data


def write(report):
    temporary=OUT/'report.json.writing'
    temporary.write_text(json.dumps(report,indent=2)+'\n')
    temporary.replace(OUT/'report.json')


def run(command,log,environment=None):
    with log.open('xb') as output:
        return subprocess.run(list(map(str,command)),cwd=ROOT,env=environment,
            stdout=output,stderr=subprocess.STDOUT).returncode


def main():
    OUT.mkdir(exist_ok=False)
    (OUT/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    frozen=manifest()
    (OUT/'source_manifest.json').write_text(json.dumps(frozen,indent=2)+'\n')
    standard=read(ROOT/'logs/reliability_render_my_world_s1001_handover_guard_20261006/source_manifest.json')
    core={key:value for key,value in standard.items() if key.startswith('src/')}
    decision_changed=any(frozen.get(key)!=value for key,value in core.items())
    assert decision_changed, 'Expected capture boundary repair absent'
    report=dict(state='RUNNING_COMPLETE_OFFLINE_SUITE',source_frozen=True,
        decision_source_matches_passing_standard_pair=False,source_files=len(frozen),
        changed_layers=['timestamped banner captures and onboard pose pairing','distinct dwell frames','OCR cache continuity and clipped-color word rescue','headless capture metadata'],
        coupled_gust_and_delay_qualified=False,full_suite_exit_code=None,rendered=[],
        baseline_matrix='logs/reliability_navigation_baseline_matrix_assets_20261006',
        hardware_qualified=False,flights_qualified=False)
    write(report)
    assert run(['/usr/bin/python3','.scratch/simulation-reliability/check_runtime_capture_scope_20261007.py'],
               OUT/'runtime_scope.log')==0
    suite=ROOT/'logs/reliability_full_banner_capture_continuity_20261007.log'
    code=run(['/usr/bin/bash','.scratch/simulation-reliability/check_full_native.sh',str(suite)],
             OUT/'full_suite_runner.log')
    report['full_suite_exit_code']=code
    report['source_unchanged']=frozen==manifest()
    write(report)
    assert report['source_unchanged'], 'Source changed during full suite'
    if code:
        report['state']='COMPLETE_OFFLINE_SUITE_FAILED';write(report);return 1
    report['state']='RUNNING_FRESH_RENDERED_COURSES';write(report)
    env=dict(os.environ,AEROTHON_RENDER_TRIAL='mission')
    env.pop('AEROTHON_CORRIDOR_ENTRY',None)
    env.pop('AEROTHON_CORRIDOR_HANDOVER',None)
    for world in ('split_corridors',):
        assert frozen==manifest(), 'Source changed before rendered course'
        output=ROOT/f'logs/reliability_render_{world}_s20261003_banner_capture_continuity_20261007'
        print('Starting full rendered '+world+' seed20261003',flush=True)
        with (OUT/f'{world}.log').open('xb') as stream:
            process=subprocess.Popen(['/usr/bin/bash','scripts/run_recorded_acceptance.sh',
                f'sim/worlds/{world}.json','20261003',str(output),
                'logs/delivery_profile_20261005.json'],cwd=ROOT,env=env,
                stdout=stream,stderr=subprocess.STDOUT)
            copied=False
            while process.poll() is None:
                if not copied and (output/'runtime_configuration_manifest.json').exists():
                    assets=output/'runtime_visual_assets';assets.mkdir(exist_ok=False)
                    values={}
                    for path in sorted(Path('/tmp/aerothon_m2_assets').glob('*')):
                        if path.is_file():
                            data=path.read_bytes();(assets/path.name).write_bytes(data)
                            values[path.name]=hashlib.sha256(data).hexdigest()
                    assert 'qr_payloads.txt' in values and 'qr_matrices.json' in values
                    (output/'runtime_visual_assets_manifest.json').write_text(json.dumps(dict(
                        captured_wall=time.time(),sha256=values,
                        source='actual owned rendered runtime after readiness'),indent=2)+'\n')
                    copied=True
                time.sleep(2)
            result=process.wait()
        archive=run(['/usr/bin/python3','.scratch/simulation-reliability/archive_recorded_source.py',output],
                    OUT/f'{world}_archive.log') if output.exists() else None
        summary=read(output/'summary.json') if (output/'summary.json').exists() else None
        report['rendered'].append(dict(world=world,seed=20261003,exit_code=result,
            archive_exit_code=archive,runtime_visual_assets_captured=copied,
            output=output.relative_to(ROOT).as_posix(),summary=summary))
        report['source_unchanged']=frozen==manifest();write(report)
        assert report['source_unchanged'], 'Source changed during rendered course'
        print('Closed '+world+' with exit '+str(result),flush=True)
    passed=all(item['exit_code']==0 and item['archive_exit_code']==0 and
        item['runtime_visual_assets_captured'] and item['summary'] and
        item['summary'].get('acceptance_pass') is True for item in report['rendered'])
    report['state']='OBSERVATION_REPAIR_RENDERED_COURSES_PASSED' if passed else 'OBSERVATION_REPAIR_RENDERED_COURSES_FAILED'
    report['overall_simulation_qualified']=False
    report['note']='Targeted split course only; standard pair, shipped and rotated must be repeated on this source. Changing-gust and broader campaign remain unqualified'
    write(report)
    return 0 if passed else 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        if (OUT/'report.json').exists():
            report=read(OUT/'report.json');report.update(state='QUALIFICATION_COORDINATOR_ERROR',error=repr(error));write(report)
        raise

