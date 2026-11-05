"""Interrupt only the owned, unarmed domain-20 offline pytest for diagnostics."""
import json,os,signal
from pathlib import Path
root=Path(__file__).resolve().parents[2]
source=root/'logs/reliability_reduced_scope_v32_source_20261008'
assert json.loads((source/'targeted_closed_review.json').read_text())['pass_navigation']
log=root/'logs/reliability_reduced_v32_full_offline_20261008.log'
assert 'F' in log.read_text().split('=== Python unit tests ===',1)[1]
matches=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    try:
        args=(proc/'cmdline').read_bytes().split(b'\0')
        env=dict(item.split(b'=',1) for item in (proc/'environ').read_bytes().split(b'\0') if b'=' in item)
        if args[1:6]!=[b'-m',b'pytest',b'sim/',b'tests/',b'-q']:continue
        if (proc/'cwd').resolve()!=root or env.get(b'ROS_DOMAIN_ID')!=b'20':continue
        matches.append(int(proc.name))
    except (OSError,ValueError):continue
assert len(matches)==1,matches
os.kill(matches[0],signal.SIGINT)
print('Interrupted owned offline pytest to retain failure assertions:',matches[0])
