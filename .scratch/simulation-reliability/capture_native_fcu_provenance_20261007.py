"""Read-only live owned FCU binary and installed source provenance."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'logs/reliability_render_shipped_s20261003_observation_repairs_20261007'
OUT=RUN/'native_fcu_provenance_20261007.json'
assert not OUT.exists()
BASE=Path.home()/'aerothon_stack/src/ardupilot'
runtime=json.loads((RUN/'runtime_configuration_manifest.json').read_text())
process=next(v['process'] for v in runtime['parameter_sources'].values()
             if Path(v['process']['args'][0]).name=='arducopter')
pid=process['pid'];proc=Path('/proc')/str(pid)
assert os.getpgid(pid)==runtime['owned_group']==process['group'], 'Require actual run ownership'
args=[a.decode() for a in (proc/'cmdline').read_bytes().split(b'\0') if a]
assert args==process['args'], 'Require unchanged captured FCU command line'
binary=(proc/'exe').resolve();raw=binary.read_bytes()
files=[]
for relative,ranges in (
    ('ArduCopter/Parameters.cpp',[(995,1002)]),
    ('ArduCopter/mode.h',[(1106,1121)]),
    ('ArduCopter/mode_guided.cpp',[(612,629),(775,828)]),
    ('libraries/AC_AttitudeControl/AC_PosControl.cpp',[(568,600),(625,689)]),
):
    path=BASE/relative;content=path.read_bytes();lines=content.decode().splitlines()
    files.append(dict(path=str(path),sha256=hashlib.sha256(content).hexdigest(),
        excerpts=[dict(first_line=a,last_line=b,lines=lines[a-1:b]) for a,b in ranges]))

def git_read(*argv):
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
    result=subprocess.run(['git','-C',str(BASE),*argv],capture_output=True,text=True,timeout=20,env=env)
    return dict(exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr)

report=dict(kind='read-only owned actual-SITL FCU provenance',captured_unix_s=time.time(),
    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    captured_runtime_manifest_sha256=hashlib.sha256((RUN/'runtime_configuration_manifest.json').read_bytes()).hexdigest(),
    process=dict(pid=pid,owned_group=runtime['owned_group'],args=args,
        cwd=str((proc/'cwd').resolve()),start_ticks=(proc/'stat').read_text().rpartition(')')[2].split()[19]),
    binary=dict(path=str(binary),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),
    source_git_head=git_read('rev-parse','HEAD'),
    source_git_tracked_status=git_read('status','--porcelain=v1','--untracked-files=no'),files=files,
    limits=['The executing binary is hashed through its owned /proc/PID/exe link; source git status and excerpts are separately recorded.',
            'This does not prove the current binary was rebuilt from every current source byte.',
            'No build, source update, parameter write, FCU control or bulk parameter read occurred.'])
OUT.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('process','binary','source_git_head','source_git_tracked_status')},indent=2))
