"""Continue the authorized seed pair and offline suite after a verified first pass.

One rendered stack runs at a time. Any failure or source change stops the chain.
This is an immediate local continuation, not a recurring automation.
"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def read(path): return json.loads(path.read_text())

def qualify(out,seed):
    summary=read(out/'summary.json');grade=read(out/'grade.json')
    config=read(out/'configuration.json');archive=read(out/'source_archive_verification.json')
    if not (summary.get('acceptance_pass') is True and grade.get('pass') is True
            and len(grade['checks'])>=22 and all(value is True for value in grade['checks'].values())
            and config['seed']==seed and config['conditions']=='calm'
            and config['payload_fixture']=='loaded' and archive.get('archive_verified') is True):
        raise RuntimeError('Full standard acceptance did not pass all required checks: '+str(out))
    if hashlib.sha256((out/archive['archive']).read_bytes()).hexdigest()!=archive['archive_sha256']:
        raise RuntimeError('Recorded source archive changed')
    for name in ('source_manifest.json','qualification_tools_manifest.json'):
        for key,expected in read(out/name).items():
            path=Path(key)
            if not path.is_absolute():path=ROOT/path
            if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
                raise RuntimeError('Source changed after qualification: '+key)
    return summary

def main():
    first_job=ROOT/'logs/reliability_standard_s20261003_handover_guard_owned_20261006'
    first=ROOT/'logs/reliability_render_my_world_s20261003_handover_guard_20261006'
    while True:
        status=read(first_job/'status.json')
        if status['state']!='RUNNING':break
        time.sleep(5)
    if status.get('exit_code')!=0 or status['state']!='COMPLETED':
        raise RuntimeError('First standard run failed or stopped; no next run was started')
    qualify(first,20261003)
    print('First full standard seed passed; starting seed 1001 sequentially',flush=True)
    subprocess.run(['/usr/bin/bash','.scratch/simulation-reliability/start_handover_guard_standard_20261006.sh','1001'],
        cwd=ROOT,check=True)
    second=ROOT/'logs/reliability_render_my_world_s1001_handover_guard_20261006'
    qualify(first,20261003);qualify(second,1001)
    print('Both full seeds passed with unchanged source; running the full offline suite',flush=True)
    subprocess.run(['/usr/bin/bash','.scratch/simulation-reliability/check_full_native.sh',
        'logs/reliability_full_handover_guard_20261006.log'],cwd=ROOT,check=True)
    qualify(first,20261003);qualify(second,1001)
    report=dict(standard_seeds=[20261003,1001],both_full_acceptances_passed=True,
        full_offline_suite_exit_code=0,source_unchanged=True,broader_campaigns_started=False,
        note='Broader campaigns, changing-gust qualification and deferred hardware remain outstanding')
    path=ROOT/'logs/reliability_standard_pair_handover_guard_20261006.json'
    with path.open('x') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps(report),flush=True)

if __name__=='__main__':main()
