"""Refresh progress from closed evidence and keep earlier snapshots."""
import datetime
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
closed = json.loads((root/'logs/reliability_command_deadline_navigation_20261007/closed_batch_review.json').read_text())
assert len(closed['trials']) == 3 and all(t['sampling_reserve_pass'] and t['navigation_pass'] and t['final_disarmed'] for t in closed['trials'])
stamp = datetime.datetime.now().strftime('%d %B %Y, %H:%M India')
text = f'''# Current progress

Current state as of {stamp}. This section supersedes historical descriptions below.

- The complete 839-file offline run closed with 1402 passed, 2 failed,
  3 skipped. Syntax, configuration and frontend checks passed. Both failed
  search fixtures omitted timestamped motion captures, which correctly kept
  the new braking gate stopped. Correcting only those teleport-fixture inputs
  passes their unchanged assertions and all 184 related checks.
- The complete suite is now rerunning on newly frozen source under
  logs/reliability_early_red_clipped_bearing_fixture_clock_qualification_20261007.
  Split and rotated rendered recordings start only after it passes. The first
  launcher reused an existing output path and ran no tests; retry 1 is active.
- The isolated deadline controller completed all three focused physical
  navigation trials. Field 4: 793.6 s, 0.753576 m corridor, 2.185071 m exclusion.
  Field 5: 811.3 s, 0.726896 m corridor, 2.224071 m exclusion. Calm 5: 867.7 s,
  0.745085 m corridor, 2.202071 m exclusion. Both corridors were traversed,
  all 13 navigation checks passed, no contacts, actual final disarm. Frozen
  source, assets and complete evidence hashes are verified. These headless
  runs do not qualify rendered perception or delivery.
- The seven remaining calm/field seeds are running with the same frozen
  candidate, physical 0.4 s delay, 0.6 s response and 0.20 s computation budget
  under logs/reliability_command_deadline_extended_navigation_20261007.
  The production controller remains unchanged during perception qualification.
- Seven perception/search files are installed. Pristine analysis pixels,
  clipped-banner bearing before area-derived range, provisional camera red
  boundaries and braking before replanning are covered by focused tests.
  Fresh rendered acceptance on these changes is still pending.
- The last pristine split recording closed 19/22 FAILED, with motor delivery
  qualified, payload error 0.11 m, 773.1 s airborne and final disarm. Return
  traversal, unexpected mode and zone ceiling failed. Its complete video,
  source and runtime assets remain archived. Older standard/shipped passes
  are historical evidence and do not qualify the current source.
- Strong changing gusts with command delay remain unqualified. The deadline
  candidate still fails the two preserved dirty/late narrow-corridor cases.
  Extra steering reserve and two batched certificate optimizations were
  rejected. No clearance, physics or acceptance assertion was relaxed.
- Final-code standard seeds 20261003/1001, shipped/rotated/split rendered
  acceptance, the corrected 200-case matrix and the final report remain open.
  Source hashes, onboard commands/telemetry and separate truth are retained.
- Requirements stay 0.70 m corridor clearance plus 0.025 m planning reserve,
  1.50 m exclusion clearance, 900 s airborne and 22 rendered acceptance checks.
  Off-axis geometry/hash stay preserved. Delivery remains motor priority with
  three attempts, full hook retraction, then continue unconfirmed. Hardware
  qualification and staged flights remain deferred.

'''
path = root/'.scratch/simulation-reliability/status.md'
path.write_text(text+'## Historical status snapshots\n\n'+path.read_text())
with (root/'VERIFICATION.md').open('a') as stream:
    stream.write('\n\n'+text)
# The mistaken rerun coordinator caught its setup error against the old
# report. Preserve that error but restore the actual closed suite verdict.
path = root/'logs/reliability_early_red_clipped_bearing_qualification_20261007/report.json'
report = json.loads(path.read_text())
if report.get('state') == 'QUALIFICATION_COORDINATOR_ERROR' and report.get('error') == "FileExistsError(17, 'File exists')":
    report['post_run_coordinator_errors'] = [dict(error=report.pop('error'),
        note='A later rerun launcher reused this output path; no tests or rendered trials ran in that launcher')]
    assert report['full_suite_exit_code'] == 1 and report['source_unchanged']
    report['state'] = 'COMPLETE_OFFLINE_SUITE_FAILED'
    path.write_text(json.dumps(report, indent=2)+'\n')
print(stamp)
