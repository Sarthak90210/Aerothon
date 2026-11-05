"""Refresh current status without replacing earlier failed evidence."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];docs=root/'.scratch/simulation-reliability'
text='''Latest continuation: the 903-file arrival-anchor/framing candidate passes
field seed 1, all navigation checks, 816.3 s airborne, corridor minimum
0.758250277 m, red minimum 2.298071264 m, zero independent fixture contacts,
both corridors and actual connected disarm. Source/assets/archive verified.
Seed 2 is running against the SAME archive; seed 3 remains pending.
Archive SHA256: 9431676002ac84aabb134924689a945a19eadee0837822cec2e3f1c7331c18c2.
These are object-level navigation trials, without rendered/motor qualification.

The preceding scoped/fine source passed seeds 2 and 3 (800.8/881.4 s),
but seed 1 exceeded time at 915.3 s; it cannot be adopted. The camera-focus
source then failed seed 1 gate braking and contacted the board during RTL
at 825.24 s. Its legacy geometric contact checkbox passed incorrectly;
the unchanged run.json contact record and closed review explicitly reject
contact-free qualification. Earlier grade files remain preserved.
The real gate crossing regression fails before the measured-arrival anchor
fix, then 227 gate/fail-closed/router tests pass with the fix. Independent
headless contact grading fails five controls before correction; 20 contact
and campaign controls pass afterward. All fixture contacts must be supplied;
missing or malformed evidence cannot qualify an empty contact history.

Native contact coverage is also incomplete in earlier acceptance recordings:
evaluation_contacts.jsonl covers PAYLOAD contacts only. New passive sensors
cover each directly collidable CAD vehicle link without changing collision
geometry or mass; two structural tests pass. A normal-startup unarmed native
smoke is testing actual native topics and ground-contact canary recording.
No mission qualification is claimed for this smoke. Existing 22/22 split
guard result remains an unchanged legacy grade, not proof of new body-contact
qualification. Future final rendered runs must include vehicle contact truth.

The scoped escape root offline archive passed 1443 tests, 3 skipped, and all
syntax/configuration/frontend checks. Archive SHA256:
8f01ab5ca6fe9ae2572bae62f6e38a6998aab016075dfc1b5eac6eb6f37db70f.
Root has changed since that checkpoint (arrival braking and contact evidence);
a new full offline run is required. No accepted final source exists.

The recent 1 s empirical reserve gust diagnostic is rejected: dirty0 and
late1 both time out without traversal; late1 minimum clearance is 0.500754 m.
The dirty-calm regression also stalls (0.822993 m minimum). Original failed
launch guard logs are retained separately. No wider lidar filter, reduced
clearance, empirical recent-reserve policy or faster delay is installed.
Strong coupled gusts remain unresolved. All five final rendered acceptance
cases, corrected 200-case campaign and accepted-source report remain pending.
'''
p=docs/'status.md';old=p.read_text(encoding='utf-8');p.write_text('# Current progress\n\n'+text+'\n## Earlier checkpoints (superseded as current status)\n\n'+old.removeprefix('# Current progress\n'),encoding='utf-8')
with (docs/'evidence_report_20261007.md').open('a',encoding='utf-8') as f:f.write('\n## Arrival braking and independent contact continuation\n\n'+text)
index=json.loads((docs/'evidence_index_20261007.json').read_text(encoding='utf-8'))
index.update(accepted_source=None,qualification_complete=False,campaign_200_qualified=False,current_continuation=dict(active='arrival-anchor/framing field seed 2, frozen 903 files',native_contact_work='unarmed normal startup smoke; native body qualification pending',full_offline_required_after_new_changes=True))
for prefix,seeds in [('scoped_fine_framing',(1,2,3)),('clipped_bearing_framing',(1,)),('arrival_anchor_framing',(1,))]:
 for seed in seeds:
  relative=f'logs/reliability_{prefix}_field_s{seed}_navigation_20261007';out=root/relative
  item=dict(path=relative,scope='object-level navigation; no rendered or motor qualification',result=json.loads((out/'report.json').read_text())['result'])
  review=out/'closed_trial_review_20261007.json'
  if review.exists():item['closed_review']=json.loads(review.read_text())
  index['runs'][f'{prefix} field {seed}']=item
(docs/'evidence_index_20261007.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
issue=docs/'issues/39-independent-vehicle-contact-qualification.md'
issue.write_text('''# Independent vehicle contact qualification
Status: ready-for-agent
Type: bug
Parent: ../spec.md

The headless board-contact fixture can pass the geometric no-contact checkbox.
Native acceptance currently records payload-only contacts, not vehicle impacts.
Require independent contacts and complete live vehicle channels; preserve all
previous grade files and failures. No final campaign until corrected targeted
acceptance passes on the same source.

## Comments
07 October: headless grading now fails absent/malformed/nonempty fixture contact
evidence. Five red controls, then 20 green contact/campaign checks. The recorded
clipped-focus field 1 board contact at 825.24 s is preserved despite its legacy
checkbox. CAD passive contact sensors have two passing structural tests; actual
native recording smoke and grading integration are in progress.
''',encoding='utf-8')
for number in (37,38):
 p=next((docs/'issues').glob(f'{number}-*.md'))
 with p.open('a',encoding='utf-8') as f:f.write('\n07 October later continuation:\n'+text)
print('Updated report, index, status and issues 37-39; accepted source remains null.')
