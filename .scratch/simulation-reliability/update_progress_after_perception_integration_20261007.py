"""Refresh local evidence pointers without modifying decision-source files."""
import datetime
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
integration=json.loads((root/'logs/reliability_early_red_clipped_bearing_integration_20261007/report.json').read_text())
assert integration['production_modified']
stamp=datetime.datetime.now().strftime('%d %B %Y, %H:%M India')
text=f'''# Current progress

Current state as of {stamp}. This section supersedes historical job descriptions below.

- The pristine-camera complete suite passed 1388 tests, 3 skipped, and all
  other offline checks. The latest production source subsequently received
  seven reviewed perception/search files; its fresh full suite is running.
- The pristine rendered split trial closed FAILED, 19/22. Motor-priority
  delivery qualified, payload error 0.11 m, flight 773.1 s, home error 0.09 m
  and actual final disarm. Return traversal, unexpected mode and zone ceiling
  failed. Exact source, video through disarm and runtime assets are archived.
- Installed repairs retain pristine image pixels, treat clipped banner
  identity as a bearing before range, expose provisional camera red edges,
  and brake unsafe search segments before replanning from measured position.
  Selected checks pass 139 banner, 130 search/routing and 94 perception tests.
  The real callback rejects all 432 labelled red-QR fixtures. Full rendered
  acceptance remains pending. No simulator truth is supplied to decisions.
- Qualification is running under
  logs/reliability_early_red_clipped_bearing_qualification_20261007. It freezes
  839 source files, runs the full suite, then records split and rotated courses.
  Standard seeds 20261003/1001 and shipped need final-source repeats afterward.
- The isolated lidar-fault observer repair passed 5 new and 29 existing checks,
  but its three physical trials are only two navigation passes and one failure.
  Field 4 completed at 791.9 s, clearance 0.716679 m; calm 5 at 872.3 s,
  0.723122 m. Both lose the 0.725 m planning reserve. Field 5 fails recovery,
  913.8 s, 0.664405 m. All source/assets/evidence verified through disarm.
  The production controller is unchanged; this is not full qualification.
- An additional 0.05 m steering-reserve candidate failed 3 of 29 existing
  checks and both preserved strong gust/delay cases. Rejected, source archived.
- Recorded certificate-to-publication delay reaches 0.18 s. An isolated
  computation-deadline candidate passes 4 new checks and 29 physical fixture
  checks with their actual zero-computation clock. Live independent-clock
  field 4/5 and calm 5 trials retain a 0.20 s budget and are running under
  logs/reliability_command_deadline_navigation_20261007. Physical delay remains
  0.4 s and response 0.6 s. Strong gust/delay qualification remains open.
- The corrected 200-case campaign remains pending targeted qualification.
  Prior failed baseline campaigns are preserved, not promoted to passes.
- Corridor clearance stays 0.70 m plus 0.025 m planning reserve, exclusion
  clearance 1.50 m, flight ceiling 900 s. Off-axis geometry/hash stay preserved
  as infeasibility regression. Motor priority and three-attempt full hook
  retract-and-continue policy remain unchanged. Hardware/flights are deferred.

'''
path=root/'.scratch/simulation-reliability/status.md'
previous=path.read_text()
path.write_text(text+'## Historical status snapshots\n\n'+previous)
with (root/'VERIFICATION.md').open('a') as stream:
    stream.write('\n\n'+text)
print(stamp)
