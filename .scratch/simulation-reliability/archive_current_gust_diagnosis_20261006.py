"""Preserve exact controller, physical fixture and scratch experiment source."""
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[2]
scratch = root/'.scratch/simulation-reliability'
paths = [root/path for path in (
    'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py',
    'src/aerothon_avoidance/avoidance/avoidance/local_planner.py',
    'sim/test_slalom_traverse.py','sim/test_corridor_stress.py')]
paths += [scratch/name for name in (
    'probe_gust_margin.py',
    'probe_gust_certificate_trace_20261006.py','check_gust_certificate_trace_20261006.sh',
    'analyse_gust_certificate_trace_20261006.py',
    'probe_gust_external_drift_conjunct_20261006.py','check_gust_external_drift_conjunct_20261006.sh',
    'probe_gust_receipt_path_20261006.py','check_gust_receipt_path_20261006.sh',
    'probe_gust_reject_and_hold_20261006.py','check_gust_reject_and_hold_20261006.sh',
    'prove_certificate_delay_wind_feedthrough_20261006.py',
    'prove_certificate_delay_wind_feedthrough_initial_20261006.py',
    'prove_certificate_delay_wind_feedthrough_before_green_20261006.py',
    'archive_current_gust_diagnosis_20261006.py')]
out = scratch/'current_source_gust_diagnosis_archive_20261006.zip'
manifest = scratch/'current_source_gust_diagnosis_archive_20261006.json'
assert not out.exists() and not manifest.exists()
sources = {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
    for path in paths:
        archive.write(path,str(path.relative_to(root)))
result = dict(archive=out.name,archive_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
              files=len(paths),sources=sources)
manifest.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(archive=result['archive'],archive_sha256=result['archive_sha256'],files=len(paths))))
