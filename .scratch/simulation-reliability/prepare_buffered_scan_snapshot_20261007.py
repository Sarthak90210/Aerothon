"""Create a new snapshot; never edit the active paired-scan batch."""
import hashlib,json,zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[2]
qualified=root/'logs/reliability_paired_scan_navigation_s5_assets_20261007'
archive=qualified/'frozen_source.zip'
review=json.loads((qualified/'source_archive_review.json').read_text())
assert review['archive_verified'] and hashlib.sha256(archive.read_bytes()).hexdigest()==review['archive_sha256']
snapshot=root/'.scratch/buffered_scan_motion_candidate_20261007'
snapshot.mkdir(exist_ok=False)
with zipfile.ZipFile(archive) as source:
    frozen=json.loads(source.read('source_manifest.json'))
    for name,sha in frozen.items():
        path=(snapshot/name).resolve();assert path.is_relative_to(snapshot.resolve())
        data=source.read(name);assert hashlib.sha256(data).hexdigest()==sha
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
provenance=json.loads((qualified/'candidate_provenance.json').read_text())
assets=provenance['missing_assets_recovered_from_verified_archive']
asset_archive=root/'logs/reliability_corrected_headless_focus_20261007/frozen_source.zip'
assert hashlib.sha256(asset_archive.read_bytes()).hexdigest()==provenance['asset_archive_sha256']
with zipfile.ZipFile(asset_archive) as source:
    for name,sha in assets.items():
        data=source.read(name);assert hashlib.sha256(data).hexdigest()==sha
        path=(snapshot/name).resolve();assert path.is_relative_to(snapshot.resolve())
        if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
module=snapshot/'src/aerothon_avoidance/avoidance/avoidance/buffered_scan_pose.py'
module.write_bytes(Path(__file__).with_name('buffered_scan_pose_candidate_20261007.py').read_bytes())
controller=snapshot/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
text=controller.read_text().replace('from avoidance.paired_scan_pose import install',
                                  'from avoidance.buffered_scan_pose import install')
controller.write_text(text)
trace=snapshot/'src/aerothon_avoidance/avoidance/avoidance/motion_forecast_trace.py'
text=trace.read_text().replace('scan_t=_node._scan_t,scan_pose=_node._scan_pose)',
    "scan_t=_node._scan_t,scan_pose=_node._scan_pose,scan_pairing_reason=getattr(_node,'_scan_pairing_reason',None),pending_scan_stamp=(_node._pending_paired_scan[0] if getattr(_node,'_pending_paired_scan',None) else None))")
trace.write_text(text)
provenance=dict(base_archive_sha256=review['archive_sha256'],asset_sha256=assets,
    modified_sha256={path.relative_to(snapshot).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (module,controller,trace)},
    production_adopted=False,physical_fixture_changed=False,required_clearance_m=.70,
    sampling_reserve_m=.025,scope='Buffer until pose brackets arrive; never extrapolate or use stale scans')
(snapshot/'candidate_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print(json.dumps(dict(snapshot=str(snapshot),source_files=len(frozen),asset_files=len(assets))))
