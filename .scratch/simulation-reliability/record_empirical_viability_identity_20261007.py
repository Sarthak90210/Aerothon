"""Record only the explicitly named diagnostic process, without mutation."""
import argparse
import datetime
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--pid',type=int,required=True)
p.add_argument('--out',type=Path,required=True)
args = p.parse_args()
proc = Path('/proc')/str(args.pid)
argv = proc.joinpath('cmdline').read_bytes().decode().split('\0')
assert len(argv)>1 and Path(argv[1]).name=='probe_gust_empirical_viability_20261007.py'
stat = proc.joinpath('stat').read_text().rsplit(') ',1)[1].split()
env = proc.joinpath('environ').read_bytes().decode().split('\0')
selected = {k:v for item in env if '=' in item for k,v in [item.split('=',1)]
            if k in ('ROS_DOMAIN_ID','PYTHONNOUSERSITE','ROS_LOCALHOST_ONLY')}
report = dict(pid=args.pid,start_time_ticks=int(stat[19]),
    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    captured_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    argv=[x for x in argv if x],environment=selected)
assert not args.out.exists()
args.out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
