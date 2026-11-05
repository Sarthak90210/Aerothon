"""Update the active checkpoint from verified closed diagnostic trials."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
review_path=root/'logs/reliability_reduced_scope_v22_source_20261008/targeted_failure_closed_review.json'
review=json.loads(review_path.read_text());assert len(review['results'])==5
assert all(r['connected_disarm'] for r in review['results'])
summary=[]
for r in review['results']:
    g=r['grade'];summary.append(dict(run=r['result']['run'],pass_navigation=g['pass_navigation'],
        failures=[k for k,v in g['checks'].items() if not v],airborne_s=g['full_grade']['flight_time_s'],
        corridor_m=g['measured_corridor_clearance_m'],connected_disarm=r['connected_disarm']))
for name in ['status.md','evidence_report_20261007.md']:
    p=base/name;s=p.read_text(encoding='utf-8')
    s=s.replace('The V23 pipeline is queued behind the final V22 trial. Its five two-worker\nsame-source targeted trials must pass before one final offline suite, five',
                'V22 is closed: all five actually disarmed; fields 1/2/3 and mild random 4\npassed navigation, while mild random 3 retained its time/return failure.\nV23 five two-worker same-source targeted trials are active and must pass\nbefore one final offline suite, five',1)
    s=s.replace('Final mild seed 4 is still active. V22 cannot qualify and no full suite is run\non it. Its flights use the isolated V22 snapshot while ROOT now matches V23.',
                'Mild random seed 4 passed navigation at 863.2 airborne seconds. Field 3\nand mild random 4 reported DEGRADED precision, a retained quality limitation.\nV22 cannot qualify and no full suite was run on it. Exact source/configuration,\noriginal grades and connected disarm are closed in its per-artifact review.\nV23 now owns ROOT and the new trials.',1)
    p.write_text(s,encoding='utf-8')
p=base/'evidence_index_20261007.json';index=json.loads(p.read_text())
index['current_continuation']['remaining']='Five V23 targeted trials, one final offline suite, five native rendered acceptances and 96 eligible campaign flights'
index['active_runs']=['logs/reliability_reduced_v23_targeted_20261008'];index['active_trial']='logs/reliability_reduced_v23_targeted_20261008';index.pop('queued_trial',None)
index.setdefault('verification',{})['v22_closed_targeted']=dict(path=str(review_path.relative_to(root)),results=summary,accepted=False)
p.write_text(json.dumps(index,indent=2),encoding='utf-8')
print('V22 closed: 4/5 navigation, all connected disarms; V23 trials active')
