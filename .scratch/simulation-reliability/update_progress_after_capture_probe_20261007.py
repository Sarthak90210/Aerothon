"""Publish current verified outcomes without changing frozen flight source."""
import datetime
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
qual = root/'logs/reliability_early_red_clipped_bearing_fixture_clock_qualification_20261007'
value = json.loads((qual/'report.json').read_text())
assert value['full_suite_exit_code'] == 0 and value['source_unchanged']
assert '1404 passed, 3 skipped' in (root/'logs/reliability_full_early_red_clipped_bearing_fixture_clock_20261007.log').read_text()
focus = json.loads((root/'logs/reliability_command_deadline_navigation_20261007/closed_batch_review.json').read_text())
extended = json.loads((root/'logs/reliability_command_deadline_extended_navigation_20261007/closed_batch_review.json').read_text())
assert focus['all_trials_disarmed'] and extended['all_trials_disarmed']
trials = focus['trials']+extended['trials']
assert len(trials) == 10 and sum(row['navigation_pass'] for row in trials) == 7
stamp = datetime.datetime.now().strftime('%d %B %Y, %H:%M India')
text = f'''# Current progress

Current state as of {stamp}. This section supersedes historical descriptions below.

- The latest complete offline suite PASSES: 1404 tests passed, 3 skipped,
  plus syntax, configuration and frontend checks. Frozen source is unchanged,
  839 files, archive verified. Five installed decision modules resolve to
  those exact frozen source files. The two earlier fixture failures were
  fixed by adding clock and motion captures to teleport tests, with all
  original assertions and production freshness checks retained.
- The fresh rendered split seed 20261003 trial passed readiness, took off
  and is searching for the target QR. It is recording through disarm under
  logs/reliability_render_split_corridors_s20261003_early_red_clipped_bearing_fixture_clock_20261007.
  Rotated acceptance follows automatically. No rendered outcome is available
  yet. Seven installed perception/search repairs have full offline coverage.
- The deadline controller closes seven navigation passes and three failures
  across all ten calm/field seeds. Every calm seed and field seeds 4/5 pass
  with the 0.725 m planning reserve. Field 1 fails at 0.625300 m clearance;
  field 2 exceeds time at 981.0 s; field 3 fails at 0.681424 m clearance.
  Exact source, assets, commands, forecasts and independent truth through
  actual disarm are verified for all ten. Production adoption is withheld.
- An actual ROS scheduling diagnostic reproduces old capture delivery during
  a slow control callback: median pose age 92 ms. A separate capture inbox
  reduces it to 10 ms and applies observations only between control ticks.
  An isolated 760-file candidate is repeating failed field seed 1 with
  unchanged geometry, physics and clearance under
  logs/reliability_capture_inbox_field1_navigation_20261007. No result yet.
- A staged normal-startup repair makes diagnostic recording optional and
  passes two startup/cleanup checks after reproducing the original KeyError.
  Normal gate integration remains pending. No root controller was changed
  during the ongoing frozen perception qualification.
- The wider lidar median filter is rejected: both coupled gust/delay cases
  still contact, and it loses thin obstacles in seven of 36 controlled cases.
  Strong gust/delay qualification remains open. Failed baseline, steering
  margin and certificate-batching alternatives are retained as failures.
- Final-code standard seeds 20261003/1001, shipped/rotated/split rendered
  acceptance with motor confirmation and measured detector rates, the
  corrected 200-case matrix and final evidence report remain unfinished.
  Older standard/shipped passes do not qualify these changed decision files.
- Corridor clearance stays 0.70 m plus 0.025 m planning reserve, exclusions
  1.50 m, airborne limit 900 s, and rendered acceptance 22 checks. Off-axis
  world/hash stay preserved. Motor priority and three-attempt full hook
  retract-and-continue remain unchanged. Hardware and flights remain deferred.

'''
path = root/'.scratch/simulation-reliability/status.md'
path.write_text(text+'## Historical status snapshots\n\n'+path.read_text(), encoding='utf-8')
with (root/'VERIFICATION.md').open('a', encoding='utf-8') as stream:
    stream.write('\n\n'+text)
print(stamp)
