"""Describe the new camera bracket, preserving every prior failed grade."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v24_source_20261008'
prov=json.loads((source/'provenance.json').read_text())
old=json.loads((root/'.scratch/reduced_scope_v23_candidate_20261008/source_manifest.json').read_text())
new=json.loads((root/'.scratch/reduced_scope_v24_candidate_20261008/source_manifest.json').read_text())
changes=dict(added=[n for n in new if n not in old],changed=[n for n in new if n in old and new[n]!=old[n]],
    removed=[n for n in old if n not in new],accepted_source=False,thresholds_unchanged=True,
    lidar_filter_unchanged=True,normal_actuators_unchanged=True,search_pacing_unchanged=True)
(source/'change_from_v23.json').write_text(json.dumps(changes,indent=2))
closed_path=root/'logs/reliability_reduced_scope_v23_source_20261008/targeted_failure_closed_review.json'
closed=json.loads(closed_path.read_text());assert len(closed['results'])==5
assert all(r['connected_disarm'] for r in closed['results'])
summary=[]
for r in closed['results']:
    g=r['grade'];summary.append(dict(run=r['result']['run'],pass_navigation=g['pass_navigation'],
        failures=[k for k,v in g['checks'].items() if not v],airborne_s=g['full_grade']['flight_time_s'],
        corridor_m=g['measured_corridor_clearance_m'],connected_disarm=r['connected_disarm']))
headline=f'''# Current checkpoint: V24 provisional

No accepted source. V24 freezes {len(new)} controlled files, archive SHA256
{prov['archive_sha256']}.
All 11 normal-startup imports match; 314 focused checks pass. The actual search
leaf reproduced a camera-only framing deadlock: the same identified board was
cut off at the bottom with FORWARD and at the top with BANNER, and the recovery
oscillated between the two. V24 brackets opposing fresh vertical crops from the
same held view and commands an intermediate angle using camera_ctrl's existing
numeric-degree protocol. It allows at most three adjustments within the existing
0 to -20 degree range. Numeric requests must match the measured camera controller
readback and settled/fresh state. Duplicate, stale, unidentified, unsettled,
moved-view, changed-bearing, side-crop and exhausted cases refuse the bracket.

Framing moves only the camera. Clipped images still cannot provide accepted
range, identity acceptance or crossing permission. Body translation, altitude,
search pacing, the .30 s trust age/.08 m/s braking checks, .70 m corridor and
1.50 m red clearance, 900 s time limit, sensor schedules, lidar filters and
actuator response are unchanged from V23.

Five two-worker V24 same-source targeted navigation trials are active. They
must all pass before one final offline suite, five full native rendered
acceptances and 96 eligible campaign flights. Reduced scope remains 120
selected, 24 negative geometry classifications and 80 weather exclusions.
Strong gusts and artificial control delay remain unresolved and excluded.
Original 200-case qualification is not claimed.

## V23 closed result

V23 fields 1/2 and mild random 4 passed navigation. Field 3 and mild random 3
failed time/unexpected mode; mild random 3 also failed return. All five actually
disarmed with zero contacts/fence breaches. Their original grades are preserved
in the exact-source per-artifact closed review. Mild random 4 reported DEGRADED
precision, retained as a quality limitation. Fixture motor delivery remains
unmeasured and unqualified. No full offline suite was run on failed V23.

High return transit measured 11.04 s for field 2 and 11.46 s for mild random 3,
versus 70.64 s in the retained V22 mild failure. The acknowledged speed lease
release is integrated and retained in V24. Remaining return searches were slow:
field 3 spent 194.96 s before alignment, while mild random 3 remained searching
through watchdog return. Passive snapshots show the opposing crop pattern;
they are not a complete 20 Hz banner ledger and do not prove an exact runtime
capture streak. The large level top-crop hypothesis had zero matching observed
examples and was not adopted. The real leaf's opposing-tilt red and focused
green results drive V24 instead.

'''
for name in ['status.md','evidence_report_20261007.md']:
    p=base/name;s=p.read_text(encoding='utf-8')
    if '# Current checkpoint: V24 provisional' not in s:p.write_text(headline+s,encoding='utf-8')
p=base/'evidence_report_20261007.md';s=p.read_text(encoding='utf-8')
s=s.replace('Finish the five targeted navigation cases and final offline suite on V23, then','Finish the five targeted navigation cases and final offline suite on V24, then')
if '| V23 field 3 |' not in s:s=s.replace('| Strong gust/delayed control |',
    '| V23 field 3 | Search 194.96 s; time/unexpected mode failed; actual disarm | Preserved failure; opposing camera crops reproduced |\n'
    '| V23 mild random 3 | High transit shortened to 11.46 s; return search still failed time/return; watchdog RTL and actual disarm | Preserved failure; camera bracket candidate unaccepted |\n'
    '| V23 mild random 4 | Navigation passed; precision landing DEGRADED | Quality limitation retained; fixture motor delivery unqualified |\n'
    '| Strong gust/delayed control |',1)
p.write_text(s,encoding='utf-8')
p=base/'evidence_index_20261007.json';index=json.loads(p.read_text())
index['current_continuation']=dict(source='V24 provisional',source_files=len(new),archive_sha256=prov['archive_sha256'],remaining='Five V24 targeted trials, one final offline suite, five native rendered acceptances and 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v24_targeted_20261008'];index['active_trial']='logs/reliability_reduced_v24_targeted_20261008';index.pop('queued_trial',None)
index['accepted_source']=None;index['qualification_complete']=False
index['reduced_scope']['classification_audit']='logs/reliability_reduced_scope_v24_source_20261008/planned_geometry_scope.json'
index.setdefault('verification',{})['v23_closed_targeted']=dict(path=str(closed_path.relative_to(root)),results=summary,accepted=False)
index['verification']['v24_startup_and_focused']=dict(startup='logs/reliability_reduced_scope_v24_source_20261008/installed_startup_imports.json',
    red='logs/reliability_return_tilt_bracket_red_20261008.log',focused='logs/reliability_v24_camera_framing_focused_20261008.log',checks=314,accepted=False)
index['verification']['v23_return_crop_diagnosis']='logs/reliability_reduced_v23_targeted_20261008/my_world_random_s3/return_top_crop_diagnosis.json'
p.write_text(json.dumps(index,indent=2),encoding='utf-8')
for name in ['08-rendered-return-clearance.md','37-search-overlapping-exclusion-escape.md']:
    with (base/'issues'/name).open('a',encoding='utf-8') as f:
        f.write('\n08 October V24 continuation: V23 closed 3/5 navigation passes; field 3 and mild random 3 time failures preserved, all actually disarmed and no contacts/fence breaches. High return speed restoration shortened transit to about 11 s but camera framing still failed. The actual FindReturnBanner leaf reproduced FORWARD bottom crop/BANNER top crop oscillation. V24 uses at most three camera-only bracket angles via the existing numeric protocol, validates measured settlement, and still rejects clipped range. 314 focused checks and 11 startup imports match the freeze. Five same-source trials active; no final offline/native/campaign acceptance yet.\n')
print(json.dumps(changes,indent=2))
