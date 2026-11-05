"""Add missing verified visual assets without changing candidate decisions."""
import hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/paired_scan_motion_candidate_20261007'
archive=root/'logs/reliability_corrected_headless_focus_20261007/frozen_source.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='ce70e282063bf91821e5e09b056f58fd9ec9584e9d06b7be307d14f0eaeb5662'
added={}
with zipfile.ZipFile(archive) as z:
    manifest=json.loads(z.read('source_manifest.json'))
    for name,sha in manifest.items():
        target=(snapshot/name).resolve();assert target.is_relative_to(snapshot.resolve())
        data=z.read(name);assert hashlib.sha256(data).hexdigest()==sha,name
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);added[name]=sha
assert (snapshot/'src/aerothon_sim/sim_gazebo/materials/qr_payloads.txt').exists()
runner=snapshot/'sim/run_braked_navigation_probe.py'
text=runner.read_text().replace('reliability_paired_scan_navigation_s5_20261007',
                              'reliability_paired_scan_navigation_s5_assets_20261007')
runner.write_text(text)
provenance=json.loads((snapshot/'candidate_provenance.json').read_text())
provenance.update(missing_assets_recovered_from_verified_archive=added,
    asset_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    first_attempt='NO_OUTCOME setup failure from missing qr_payloads.txt; never a flight qualification')
provenance['modified_sha256']['sim/run_braked_navigation_probe.py']=hashlib.sha256(runner.read_bytes()).hexdigest()
(snapshot/'candidate_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print(json.dumps(dict(added=len(added),decision_controller_changed=False,required_qr_assets_present=True)))
