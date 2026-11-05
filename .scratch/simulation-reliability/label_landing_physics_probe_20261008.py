"""Record the green diagnostic and limitations without claiming reproduction."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
original=root/'logs/reliability_v21_precision_physics_red_20261008.log'
if original.exists():
    target=root/'logs/reliability_precision_physics_probe_green_20261008.log'
    if not target.exists():target.write_bytes(original.read_bytes())
    review=dict(result='PASS before any proposed landing metric change',visual_lock_sim_s=8.6,
        reproduced_field_seed_2_timeout=False,qualification_evidence=False,
        original_filename_mislabel='red filename was chosen before the diagnostic ran; content is green',
        limits=['Initial home reference was constructed from the fixture model rather than replayed from ScanStartQR',
               'Ideal immediate camera delivery was used instead of recorded processing latency',
               'Dropped frames zeroed the QR offset rather than retaining the previous delivered value',
               'Actual returning pose and correlated GPS bias were not replayed'],
        source=str(original.relative_to(root)),sha256=hashlib.sha256(original.read_bytes()).hexdigest())
    (root/'logs/reliability_precision_physics_probe_review_20261008.json').write_text(json.dumps(review,indent=2))
    print('Green probe preserved and explicitly labelled; not a reproduction or qualification')
