"""Record all five sealed navigation results without claiming delivery."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v38_source_20261008'
review=json.loads((source/'targeted_closed_review.json').read_text())
assert review['pass_navigation'] and review['source_unchanged'] and review['source_archive_verified']
assert len(review['results'])==5
rows=[]
for r in review['results']:
    assert len(r['checks'])==13 and all(r['checks'].values())
    assert r['configuration']['rtf']==1 and r['configuration']['vel_response_s']==.6
    assert r['configuration']['injected_command_delay_s']==0
    precision=json.loads((root/r['path']/'run.json').read_text())['result']['landing_precision']
    rows.append(dict(weather=r['weather'],seed=r['seed'],corridor_clearance_m=r['corridor_clearance_m'],red_clearance_m=r['red_clearance_m'],flight_time_s=r['flight_time_s'],precision=precision,path=r['path']))
note='''## V38 targeted navigation verified

All five exact-source cases passed all 13 navigation checks, with actual
connected disarm, zero contacts/fence breaches and verified source/archive
hashes. Normal actuator response 0.6 s, zero additional transport queue,
camera 20 Hz/lidar 10 Hz, 0.20 s computation budget and RTF1 are retained.
The table is navigation-only evidence. Rendered perception and motor delivery
were not exercised. Random seed 4 retains DEGRADED landing quality.

| Preset | Seed | Corridor metres | Red metres | Airborne seconds |
|---|---:|---:|---:|---:|
'''
for r in rows:note+=f"| {r['weather']} | {r['seed']} | {r['corridor_clearance_m']:.9f} | {r['red_clearance_m']:.9f} | {r['flight_time_s']} |\n"
note+='\nThe complete reduced offline suite is running. Five native 22/22\nacceptances and 96 eligible campaign flights remain pending. No source is\naccepted yet and no original 200-case qualification is claimed.\n\n'
for name in ['status.md','evidence_report_20261007.md']:
    f=base/name;s=f.read_text(encoding='utf-8')
    if '## V38 targeted navigation verified' not in s:f.write_text(note+s,encoding='utf-8')
f=base/'evidence_index_20261007.json';index=json.loads(f.read_text(encoding='utf-8'))
index['active_runs']=[];index['active_trial']='logs/reliability_reduced_v38_full_offline_20261008.log'
index['verification']['v38_targeted_closed_review']='logs/reliability_reduced_scope_v38_source_20261008/targeted_closed_review.json'
index['verification']['v38_targeted_navigation']=rows
index['current_continuation']['remaining']='Complete reduced-scope offline suite, five rendered acceptances, 96 eligible campaign flights'
f.write_text(json.dumps(index,indent=2),encoding='utf-8')
print(json.dumps(dict(navigation_passes=5,min_corridor_m=min(r['corridor_clearance_m'] for r in rows),min_red_m=min(r['red_clearance_m'] for r in rows),accepted_source=False)))
