"""Preserve the exact scratch source versions referenced by probe outputs."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
directory=HERE/'terminal_prototype_source_archive_20261006'
directory.mkdir(exist_ok=True)
current=(HERE/'probe_certificate_terminal_20261006.py').read_bytes()
old=current.replace(b"    old = '        if not motion_clear((vx,vy)):'",b"    old = '    if not motion_clear((vx,vy)):'")
begin=old.index(b"    replacement = ''' + repr('''")
end=old.index(b"''') + '''",begin)
block=old[begin:end]
block=block.replace(b"repr('''        def",b"repr('''    def")
block=b'\n'.join(line[4:] if i>0 and line.startswith(b'    ') else line for i,line in enumerate(block.split(b'\n')))
old=old[:begin]+block+old[end:]
versions={hashlib.sha256(content).hexdigest():content for content in (current,old,
    (HERE/'probe_proactive_position_hold_20261006.py').read_bytes(),(HERE/'probe_gust_margin.py').read_bytes())}
for sha,content in versions.items():
    destination=directory/(sha+'.py')
    if destination.exists():assert destination.read_bytes()==content
    else:destination.write_bytes(content)
report=[]
for name in ('reliability_gust_dirty_delayed_terminal_hold_20261006.json',
             'reliability_gust_dirty_terminal_raw_zero_20261006.json',
             'reliability_gust_dirty_rate_alternatives_retry1_20261006.json',
             'reliability_gust_dirty_proactive_hold_retry1_20261006.json'):
    path=ROOT/'logs'/name
    if not path.exists():continue
    data=json.loads(path.read_text())
    scratch=[(key,sha) for key,sha in data['source_sha256'].items() if key.startswith('.scratch/')]
    for key,sha in scratch:
        report.append(dict(output=name,source=key,sha256=sha,exact_source_archived=sha in versions))
        assert sha in versions,(name,key,sha)
print(json.dumps(report,indent=2))
