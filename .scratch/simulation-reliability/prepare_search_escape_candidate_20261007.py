"""Freeze only the reproduced search repair on the unchanged inbox candidate."""
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[2]
base = root/'logs/reliability_capture_inbox_source_20261007'
snapshot = root/'.scratch/search_escape_candidate_20261007'
out = root/'logs/reliability_search_escape_source_20261007'
snapshot.mkdir(exist_ok=False)
out.mkdir(exist_ok=False)
provenance = json.loads((base/'candidate_provenance.json').read_text())
archive_path = base/'frozen_source.zip'
assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == provenance['source_archive_sha256']
with zipfile.ZipFile(archive_path) as archive:
    manifest = json.loads(archive.read('source_manifest.json'))
    for name, sha in manifest.items():
        data = archive.read(name)
        assert hashlib.sha256(data).hexdigest() == sha
        target = snapshot/name
        assert target.resolve().is_relative_to(snapshot.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
for name, sha in provenance['asset_sha256'].items():
    data = (root/'.scratch/capture_inbox_candidate_20261007'/name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == sha
    target = snapshot/name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
name = 'src/aerothon_mission/mission_bt/mission_bt/leg_router.py'
target = snapshot/name
before = target.read_text()
old = '        px, py = mav.pos()[:2]\n        left = self.lead_m'
assert before.count(old) == 1
after = before.replace(old, '''        px, py = mav.pos()[:2]
        # Finish the planned escape before applying look-ahead. A waypoint
        # inside an overlapping margin is still part of the escape sequence.
        blocks = routing_obstacles(self._exclusions(mav), self.clearance_m)
        if any(x0 <= px <= x1 and y0 <= py <= y1 for x0,x1,y0,y1 in blocks):
            return wx, wy
        left = self.lead_m''')
old = '        for x0,x1,y0,y1 in containing:'
assert after.count(old) == 1
after = after.replace(old, '''        # route_leg leaves the first containing margin, then replans the
        # remaining overlapping margins. Requiring all their different
        # nearest exits at once rejects every command in the sequence.
        for x0,x1,y0,y1 in containing[:1]:''')
compile(after, name, 'exec')
target.write_text(after)
(out/'leg_router.before.py').write_text(before)
(out/'leg_router.candidate.py').write_text(after)
manifest = {name: hashlib.sha256((snapshot/name).read_bytes()).hexdigest() for name in manifest}
with zipfile.ZipFile(out/'frozen_source.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('source_manifest.json', json.dumps(manifest, indent=2)+'\n')
    for name in sorted(manifest):
        archive.writestr(name, (snapshot/name).read_bytes())
with zipfile.ZipFile(out/'frozen_source.zip') as archive:
    assert all(hashlib.sha256(archive.read(name)).hexdigest() == sha for name,sha in manifest.items())
provenance.update(source_archive_sha256=hashlib.sha256((out/'frozen_source.zip').read_bytes()).hexdigest(),
    source_archive_verified=True, source_changes=provenance['source_changes']+['sequential observed exclusion escape'],
    source_files=len(manifest), production_modified=False, flight_qualified=False)
(out/'candidate_provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
runner = (root/'.scratch/simulation-reliability/run_capture_inbox_field23_batch_20261007.py').read_text()
runner = runner.replace('capture_inbox_candidate_20261007', 'search_escape_candidate_20261007')
runner = runner.replace('reliability_capture_inbox_source_20261007', 'reliability_search_escape_source_20261007')
runner = runner.replace('reliability_capture_inbox_field23_navigation_20261007', 'reliability_search_escape_field2_navigation_20261007')
start = runner.index('import ast\n')
end = runner.index('before=json.loads', start)
runner = runner[:start]+runner[end:]
runner = runner.replace("[('field',2),('field',3)]", "[('field',2)]")
runner = runner.replace('ros_domain=178+i', 'ros_domain=189+i')
runner = runner.replace('jobs=2', 'jobs=1').replace('max_workers=2', 'max_workers=1')
path = root/'.scratch/simulation-reliability/run_search_escape_field2_20261007.py'
with path.open('x') as handle:
    handle.write(runner)
print(json.dumps(dict(snapshot=str(snapshot), archive_sha256=provenance['source_archive_sha256'], source_files=len(manifest))))
