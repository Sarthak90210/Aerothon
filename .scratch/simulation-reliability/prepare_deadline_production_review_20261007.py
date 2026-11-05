"""Prepare navigator changes without overwriting active production evidence."""
import difflib
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[2]
candidate = root/'.scratch/command_deadline_candidate_20261007'
out = root/'logs/reliability_deadline_production_review_20261007'
out.mkdir(exist_ok=False)
archive = root/'logs/reliability_command_deadline_source_20261007/frozen_source.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == 'fa239ceba76e5ad03d34229197703bcd5972389111d76ec7a1c9b0df7ac164b9'
with zipfile.ZipFile(archive) as handle:
    frozen = json.loads(handle.read('source_manifest.json'))
    for name, sha in frozen.items():
        assert hashlib.sha256(handle.read(name)).hexdigest() == sha
        assert hashlib.sha256((candidate/name).read_bytes()).hexdigest() == sha
base = 'src/aerothon_avoidance/avoidance/avoidance/'
names = ('velocity_controller.py', 'buffered_scan_pose.py', 'paired_scan_pose.py',
         'fast_connected_planner_candidate.py', 'independent_ros_clock_candidate.py',
         'motion_forecast_trace.py')
changes = []
for name in names:
    relative = base+name
    data = (candidate/relative).read_bytes()
    before = (root/relative).read_bytes() if (root/relative).exists() else b''
    if name == 'velocity_controller.py':
        text = data.decode()
        old = "    trace = MotionForecastTrace(node,os.environ['AEROTHON_MOTION_FORECAST_OUT'])"
        assert text.count(old) == 1
        text = text.replace(old, "    trace_path = os.environ.get('AEROTHON_MOTION_FORECAST_OUT')\n    trace = MotionForecastTrace(node,trace_path) if trace_path else None")
        assert text.count('        trace.close()') == 1
        text = text.replace('        trace.close()', '        if trace is not None:\n            trace.close()')
        data = text.encode()
        compile(text, relative, 'exec')
    staged = out/'candidate'/relative
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_bytes(data)
    if before:
        saved = out/'before'/relative
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_bytes(before)
    diff = ''.join(difflib.unified_diff(before.decode().splitlines(True), data.decode().splitlines(True),
        fromfile='production/'+relative, tofile='proposed/'+relative))
    (out/(name+'.diff')).write_text(diff)
    changes.append(dict(path=relative, before_sha256=hashlib.sha256(before).hexdigest() if before else None,
        tested_candidate_sha256=frozen[relative], proposed_sha256=hashlib.sha256(data).hexdigest(),
        additional_change='Optional diagnostic recorder at startup' if name=='velocity_controller.py' else None))
report = dict(production_modified=False, candidate_archive_verified=True, files=changes,
    scope='Prepared navigator proposal only, not a production or rendered acceptance result',
    constraints=dict(corridor_clearance_m=.70, sampling_reserve_m=.025, physical_delay_s=.4, response_s=.6),
    blockers=['Remaining seven navigation cases must close and preserve the planning reserve',
        'Current perception qualification owns frozen production source; do not install during its runs',
        'Gate braking is currently a headless-process substitution and still needs normal mission integration',
        'Optional recorder startup adjustment needs verification before adoption',
        'Strong gust-plus-delay failures remain unresolved; this proposal does not qualify them',
        'Integrated final source needs full offline and rendered acceptance, followed by the corrected matrix'],
    preserved_production_layers=['current camera capture and clipped-banner fixes',
        'provisional camera exclusions and stop-before-replan', 'motor-priority delivery and retract-and-continue'])
(out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(dict(files=len(changes), production_modified=False, candidate_archive_verified=True)))
