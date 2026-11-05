"""Freeze the exact physical fixture and empirical-reserve experiment."""
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[2]
paths = [root/path for path in (
    'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py',
    'src/aerothon_avoidance/avoidance/avoidance/local_planner.py',
    'src/aerothon_avoidance/avoidance/avoidance/scan_geometry.py',
    'src/aerothon_sim/sim_gazebo/sim_gazebo/corruptions.py',
    'sim/test_slalom_traverse.py','sim/test_corridor_stress.py',
    '.scratch/simulation-reliability/probe_gust_margin.py',
    '.scratch/simulation-reliability/probe_gust_empirical_viability_20261007.py',
    '.scratch/simulation-reliability/probe_gust_empirical_viability_initial_20261007.py',
    '.scratch/simulation-reliability/check_gust_empirical_viability_20261007.sh',
    '.scratch/simulation-reliability/analyse_empirical_viability_run_20261007.py',
    '.scratch/simulation-reliability/archive_empirical_viability_sources_20261007.py')]
out = root/'.scratch/simulation-reliability/empirical_viability_sources_20261007.zip'
manifest = out.with_suffix('.json')
assert not out.exists() and not manifest.exists()
sources = {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
    for path in paths:
        archive.write(path,str(path.relative_to(root)))
result = dict(archive=out.name,archive_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
              sources=sources,files=len(paths))
manifest.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(archive=result['archive'],archive_sha256=result['archive_sha256'],files=len(paths))))
