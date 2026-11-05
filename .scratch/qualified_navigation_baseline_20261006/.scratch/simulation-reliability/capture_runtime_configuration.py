"""Copy configuration from this owned simulator group; never read device state."""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

out=Path(sys.argv[1]).resolve()
processes=[]
for entry in Path('/proc').glob('[0-9]*'):
    try:
        args=[a.decode(errors='replace') for a in (entry/'cmdline').read_bytes().split(b'\0') if a]
        ppid=int(next(line.split()[1] for line in (entry/'status').read_text().splitlines() if line.startswith('PPid:')))
        processes.append(dict(pid=int(entry.name),ppid=ppid,args=args,group=os.getpgid(int(entry.name))))
    except (OSError,StopIteration,ValueError):pass
harness=next((p for p in processes if 'scripts/run_recorded_acceptance.sh' in p['args']
              and any(Path(a).resolve()==out for a in p['args'] if a.startswith('logs/'))),None)
if harness is None:raise SystemExit('This output has no active owned rendered harness')
stack=next((p for p in processes if p['ppid']==harness['pid']
            and 'scripts/launch_level6_sim.sh' in p['args']),None)
if stack is None:raise SystemExit('Owned simulator stack group not found')
members=[p for p in processes if p['group']==stack['group']]
directory=out/'runtime_parameters'
directory.mkdir(exist_ok=False)
provenance={}
for process in members:
    args=process['args']
    sources=[]
    for i,arg in enumerate(args[:-1]):
        if arg=='--params-file':sources.append(Path(args[i+1]))
        if arg=='--defaults':sources.extend(Path(p) for p in args[i+1].split(','))
    for source in sources:
        if not source.is_file():raise SystemExit(f'Loaded parameter file disappeared: {source}')
        target=directory/f'{process["pid"]}_{source.name}'
        if target.exists():continue
        shutil.copyfile(source,target)
        provenance[str(target.relative_to(out))]=dict(source=str(source),process=process)
assets={}
for path in out.rglob('*'):
    if path.is_file() and (path.parent==directory or 'vehicle_meshes' in path.parts
                          or path.name in ('flight_world.sdf','flight_vehicle.sdf','airframe.json',
                              'flight_conditions.json','flight_conditions.parm','layout.json',
                              'world_spec.json','frozen_calibration.json','configuration.json')):
        assets[str(path.relative_to(out))]=hashlib.sha256(path.read_bytes()).hexdigest()
(out/'runtime_configuration_manifest.json').write_text(json.dumps(dict(
    owned_group=stack['group'],sha256=assets,parameter_sources=provenance),indent=2)+'\n')
print(json.dumps(dict(parameter_files=len(provenance),hashed_configuration_assets=len(assets),owned_group=stack['group'])))
