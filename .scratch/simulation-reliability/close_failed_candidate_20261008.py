"""Preserve a closed failed candidate and record its successor without regrading."""
import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from qualification_evidence import recorded_disarm
old,new=sys.argv[1:3];parent=root/f'logs/reliability_reduced_{old}_targeted_20261008';report=json.loads((parent/'report.json').read_text());assert report['pass_navigation'] is False
manifest=json.loads((root/f'.scratch/reduced_scope_{old}_candidate_20261008/source_manifest.json').read_text());records=[]
for result in report['results']:
 run=parent/result['run'];assert json.loads((run/'source_manifest.json').read_text())==manifest
 rows=[json.loads(s) for s in (run/'onboard.jsonl').read_text(encoding='utf-8').splitlines()];disarm=recorded_disarm(rows);assert disarm
 records.append(dict(result=result,connected_disarm=disarm,configuration=json.loads((run/'configuration.json').read_text()),operator_stop=json.loads((run/'operator_stop.json').read_text()),files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in run.iterdir() if p.is_file()}))
closed=root/f'logs/reliability_reduced_scope_{old}_source_20261008/targeted_diagnostic_closed_review.json'
with closed.open('x',encoding='utf-8') as f:json.dump(dict(accepted_source=False,pass_navigation=False,source_unchanged=report['source_unchanged'],source_files=len(manifest),all_connected_disarmed=True,results=records),f,indent=2)
prov=json.loads((root/f'logs/reliability_reduced_scope_{new}_source_20261008/provenance.json').read_text())
base=root/'.scratch/simulation-reliability';p=base/'evidence_index_20261007.json';idx=json.loads(p.read_text(encoding='utf-8'));idx['verification'][f'{old}_targeted_closed_review']=str(closed.relative_to(root)).replace('\\','/');idx['active_runs']=[f'logs/reliability_reduced_{new}_targeted_20261008/my_world_random_s3'];idx['current_continuation']=dict(source=f'{new.upper()} provisional',source_files=prov['files'],archive_sha256=prov['archive_sha256'],remaining='Targeted navigation, one final offline suite, five rendered acceptances and reduced campaign');p.write_text(json.dumps(idx,indent=2),encoding='utf-8')
p=base/'status.md';text=p.read_text(encoding='utf-8');p.write_text(f'''# Current checkpoint — {new.upper()} provisional

No accepted source. Frozen {prov['files']} files; archive SHA256
{prov['archive_sha256']}.
Retained mild-weather random 3 is active with normal timing and actuators.
Return framing now consumes distinct fresh onboard-pose-associated captures
during yaw settlement as well as dwell. Existing three-capture requirement,
0.5 m same-XY raise, maximum three climbs and all identity/lidar checks remain.
Top-cropped lettering during a turn guides only bounded framing recovery.
258 return/gate checks pass, including the new red/green real-leaf control
and stale, replay, tilted and outbound rejection. No final offline run yet.
{old.upper()} failed return/time acceptance; recorded RTL and connected disarm verified.
Original failures, source/configuration hashes and artifact hashes are closed.
Strong gusts and artificial delay remain unresolved and excluded.
Five targeted cases, five rendered acceptances and 96 campaign flights pending;
24 negative geometry classifications and 80 weather exclusions are not passes.

## Prior checkpoints

'''+text,encoding='utf-8')
p=base/'evidence_report_20261007.md';text=p.read_text(encoding='utf-8');text=text.replace(f'active provisional source is {old.upper()}:',f'active provisional source is {new.upper()}:').replace(f'reliability_reduced_scope_{old}_source_20261008',f'reliability_reduced_scope_{new}_source_20261008').replace(f'reliability_reduced_{old}_targeted_20261008',f'reliability_reduced_{new}_targeted_20261008')
oldprov=json.loads((root/f'logs/reliability_reduced_scope_{old}_source_20261008/provenance.json').read_text());text=text.replace(oldprov['archive_sha256'],prov['archive_sha256']);last_grade=json.loads((parent/report['results'][0]['run']/'navigation_grade.json').read_text())
summary=f"{sum(last_grade['checks'].values())}/{len(last_grade['checks'])} navigation checks; flight {last_grade['full_grade']['flight_time_s']} s; failures: {', '.join(report['results'][0]['navigation_failures'])}; actual disarm; stop request preserved"
text=text.replace('| Strong gust/delayed control |',f'| {old.upper()} retained random 3 | {summary} | Preserved failure; remains in scope |\n| Strong gust/delayed control |')
text=text.replace('Required thresholds remain',f'''{new.upper()} extends the existing bounded return height recovery to yaw settlement.
Three distinct fresh identified top-cropped level-camera captures may raise
0.5 m at unchanged XY and retry the captured world bearing; maximum three
climbs and all subsequent full-identity/range/lidar requirements remain.
The real leaf reproduced the missed turn captures before the fix. The final
focused return/gate set passes 258, including stale/replay/tilted/outbound controls.

Required thresholds remain''');p.write_text(text,encoding='utf-8')
print(f'{old} failure closed; {new} provisional, no qualification claimed')
