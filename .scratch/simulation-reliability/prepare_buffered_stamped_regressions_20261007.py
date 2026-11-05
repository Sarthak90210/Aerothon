"""Archive rejected source, then prepare measurement-stamped isolated fixtures."""
import hashlib,json,zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/buffered_scan_motion_candidate_20261007'
out=root/'logs/reliability_buffered_stamped_fixture_preparation_20261007'
out.mkdir(exist_ok=False)
base=root/'logs/reliability_paired_scan_navigation_s5_assets_20261007/frozen_source.zip'
with zipfile.ZipFile(base) as archive:
    names=set(json.loads(archive.read('source_manifest.json')))
names.add('src/aerothon_avoidance/avoidance/avoidance/buffered_scan_pose.py')
manifest={name:hashlib.sha256((snapshot/name).read_bytes()).hexdigest() for name in sorted(names)}
archive_path=out/'rejected_regression_source.zip'
with zipfile.ZipFile(archive_path,'x',zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('source_manifest.json',json.dumps(manifest,indent=2)+'\n')
    for name in manifest:archive.writestr(name,(snapshot/name).read_bytes())
with zipfile.ZipFile(archive_path) as archive:
    assert all(hashlib.sha256(archive.read(name)).hexdigest()==sha for name,sha in manifest.items())
(out/'rejected_regressions.log').write_bytes((root/'logs/reliability_buffered_scan_regressions_owned_20261007/output.log').read_bytes())
fixtures=root/'.scratch/buffered_stamped_regression_fixtures_20261007'
fixtures.mkdir(exist_ok=False)
changed={}
for name in ('test_corridor_clearance_contract.py','test_slalom_traverse.py',
             'test_velocity_command_delay.py','test_fcu_navigation_velocity.py',
             'test_fcu_velocity_sample_alignment.py','test_local_planner.py'):
    original=(root/'sim'/name).read_bytes();text=original.decode()
    if name=='test_corridor_clearance_contract.py':
        old='pose=PoseStamped();pose.pose.orientation.w=1.0;c._on_pose(pose)'
        new='pose=PoseStamped();pose.header.stamp.sec=1;pose.pose.orientation.w=1.0;c._on_pose(pose)'
        assert old in text;text=text.replace(old,new)
        old="c.scan.header.frame_id='base_link'"
        assert old in text;text=text.replace(old,old+'\n    c.scan.header.stamp.sec=1')
    if name=='test_slalom_traverse.py':
        old='self.node._on_pose(pose)'
        # Both loops now publish capture times. Integration and assertions stay intact.
        assert text.count(old)==2
        lines=text.splitlines()
        for i in reversed(range(len(lines))):
            if lines[i].strip()==old:
                indent=lines[i][:-len(lines[i].lstrip())]
                lines[i:i]=[indent+'pose.header.stamp.sec=int(t)',
                            indent+'pose.header.stamp.nanosec=int(round((t-int(t))*1e9))']
        text='\n'.join(lines)+'\n'
        old='self.node._on_scan(scan_at(x, y, yaw, rects))'
        assert text.count(old)==1
        text=text.replace(old,'scan=scan_at(x, y, yaw, rects)\n                scan.header.stamp.sec=int(t)\n                scan.header.stamp.nanosec=int(round((t-int(t))*1e9))\n                self.node._on_scan(scan)')
    if name=='test_fcu_navigation_velocity.py':
        old='c._on_pose(p)'
        assert text.count(old)==3
        text=text.replace(old,'p.header.stamp.sec=int(c._now());p.header.stamp.nanosec=int(round((c._now()-int(c._now()))*1e9));c._on_pose(p)')
    path=fixtures/name;path.write_text(text)
    changed[name]=dict(original_sha256=hashlib.sha256(original).hexdigest(),
                      fixture_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                      changed=original!=path.read_bytes())
report=dict(rejected_source_archive_verified=True,source_files=len(manifest),
    rejected_archive_sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest(),
    earlier_result='23 passed, 6 failed; unstamped fixtures',fixtures=changed,
    production_modified=False,controller_modified=False,physical_fixture_or_assertions_changed=False)
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
