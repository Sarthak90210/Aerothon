#!/usr/bin/env python3
"""Run the requested navigation matrix after rendered targeted acceptance passes."""
import argparse
import hashlib
import json
import signal
import sys
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from queue import Queue

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import world_spec as W
from check_corridor_clearance import audit
from fly_headless import fly,stop_all
from campaign_record import source_manifest


def verify_targeted_runs(paths, root=ROOT):
    """Only current drone code qualified on both requested standard seeds."""
    summaries = [json.loads((p/'summary.json').read_text()) for p in paths]
    if not all(s.get('acceptance_pass') and s.get('motor_delivery_qualified')
               and s.get('final_armed') is False for s in summaries):
        raise ValueError('Both targeted full acceptances must pass and disarm')
    if {s.get('configuration', {}).get('seed') for s in summaries} != {20261003, 1001}:
        raise ValueError('Targeted seeds must be 20261003 and 1001')
    if not all(s.get('configuration', {}).get('conditions') == 'calm' and
               Path(s.get('configuration', {}).get('world', '')).name == 'my_world.json'
               for s in summaries):
        raise ValueError('Targeted runs must use the standard calm my_world course')
    manifests = [json.loads((p/'source_manifest.json').read_text()) for p in paths]
    if manifests[0] != manifests[1]:
        raise ValueError('Targeted runs have different recorded source')
    core = {name: sha for name, sha in manifests[0].items() if name.startswith('src/')}
    if not core:
        raise ValueError('No recorded drone source')
    for name, expected in core.items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Drone source changed since targeted qualification: '+name)
    return dict(qualified_seeds=[20261003, 1001], drone_source_files_verified=len(core))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--targeted',nargs=2,type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('-j',type=int,default=3)
    p.add_argument('--rtf',type=float,default=4.)
    args=p.parse_args()
    if not 1 <= args.j <= 16:
        p.error('Use 1 to 16 workers; each receives a distinct ROS domain')
    try:
        gate = verify_targeted_runs(args.targeted)
    except (ValueError, OSError) as e:
        raise SystemExit(str(e)) from e
    args.out.mkdir(parents=True,exist_ok=False)
    (args.out/'targeted_gate.json').write_text(json.dumps(gate, indent=2))
    signal.signal(signal.SIGINT,stop_all)
    signal.signal(signal.SIGTERM,stop_all)
    manifest=source_manifest(ROOT)
    (args.out/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
    classified=[]
    work=[]
    for path in sorted((ROOT/'sim/worlds').glob('*.json')):
        try:errors,warnings=W.validate(W.load(path))
        except (ValueError,TypeError,KeyError) as e:errors,warnings=[repr(e)],[]
        item=dict(world=path.name,validation_errors=errors,warnings=warnings)
        item['geometry']=[] if errors else [audit(path,lane_key=lane) for lane in ('corridor','return_corridor')]
        blocked=any(g['classification']=='geometrically blocked' for g in item['geometry'])
        item['classification']='invalid fixture' if errors else 'infeasible at 0.70 m' if blocked else 'navigation trial required'
        classified.append(item)
        for conditions in ('calm','field','worst','random'):
            for seed in range(1,6):
                if errors or blocked:
                    print(f'{path.stem}_{conditions}_s{seed}: CLASSIFIED {item["classification"]}',flush=True)
                else:work.append((path,conditions,seed))
    (args.out/'classification.json').write_text(json.dumps(classified,indent=2))
    results=[]
    domains=Queue()
    # Keep DDS ports below the host's ephemeral range even at 16 workers.
    for domain in range(40,40+args.j):
        domains.put(domain)
    def run(index,trial):
        path,conditions,seed=trial
        domain=domains.get()
        try:return fly(path,conditions,seed,args.out,args.rtf,1200.,domain,navigation_only=True)
        except Exception as e:
            return dict(run=f'{path.stem}_{conditions}_s{seed}',navigation_pass=False,
                        result='RUNNER_ERROR',error=repr(e))
        finally:
            domains.put(domain)
    with ThreadPoolExecutor(max_workers=args.j) as pool:
        futures=[pool.submit(run,i,trial) for i,trial in enumerate(work)]
        for future in as_completed(futures):
            result=future.result();results.append(result)
            (args.out/'summary.json').write_text(json.dumps(results,indent=2))
            print(json.dumps(result),flush=True)
    # Compare after clearing the cache so the recorded source freeze is checked.
    source_manifest.cache_clear()
    unchanged=manifest==source_manifest(ROOT)
    report=dict(requested_trials=len(classified)*20,executed_trials=len(results),
        classified_without_flight=(len(classified)*20-len(results)),source_unchanged=unchanged,
        navigation_passes=sum(bool(r.get('navigation_pass')) for r in results),
        failures=[r for r in results if not r.get('navigation_pass')],
        rendered_perception_qualified=False,motor_delivery_qualified=False)
    (args.out/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    return 0 if unchanged and not report['failures'] else 1


if __name__=='__main__':raise SystemExit(main())
