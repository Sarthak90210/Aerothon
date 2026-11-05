"""Create an isolated registration experiment from exact closed flight bytes."""
import hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
archive=root/'logs/reliability_motion_forecast_navigation_s3_20261007/frozen_source.zip'
snapshot=root/'.scratch/paired_scan_motion_candidate_20261007'
snapshot.mkdir(exist_ok=False)
with zipfile.ZipFile(archive) as z:
    frozen=json.loads(z.read('source_manifest.json'))
    for name,sha in frozen.items():
        path=(snapshot/name).resolve();assert path.is_relative_to(snapshot.resolve())
        data=z.read(name);assert hashlib.sha256(data).hexdigest()==sha,name
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
module=snapshot/'src/aerothon_avoidance/avoidance/avoidance/paired_scan_pose.py'
module.write_bytes(Path(__file__).with_name('paired_scan_pose_candidate_20261007.py').read_bytes())
controller=snapshot/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
text=controller.read_text();needle='    node = VelocityController()\n'
assert text.count(needle)==1
text=text.replace(needle,needle+'    from avoidance.paired_scan_pose import install\n    install(node)\n')
controller.write_text(text)
runner=snapshot/'sim/run_braked_navigation_probe.py'
text=runner.read_text().replace('reliability_motion_forecast_navigation_s3_20261007',
    'reliability_paired_scan_navigation_s5_20261007').replace("'calm',3,out", "'calm',5,out")
text=text.replace('my_world_calm_s1/source_manifest.json','my_world_calm_s5/source_manifest.json')
runner.write_text(text)
trace=snapshot/'src/aerothon_avoidance/avoidance/avoidance/motion_forecast_trace.py'
text=trace.read_text().replace('wind_world=_node._wind_world.tolist(),wind_rate_world=_node._wind_rate_world.tolist())',
    'wind_world=_node._wind_world.tolist(),wind_rate_world=_node._wind_rate_world.tolist(),scan_t=_node._scan_t,scan_pose=_node._scan_pose)')
trace.write_text(text)
provenance=dict(base_archive=str(archive),base_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    scope='Capture-time lidar pose pairing only; original clearance, actuator response, delay and physics retained',
    modified_sha256={str(p.relative_to(snapshot)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (module,controller,runner,trace)},production_adopted=False)
(snapshot/'candidate_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print(json.dumps(dict(snapshot=str(snapshot),base_files=len(frozen),modified=list(provenance['modified_sha256']))))
