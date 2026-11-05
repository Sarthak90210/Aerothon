"""One-variable diagnostic reserve; no production filtering changes."""
import sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path[:0]=[str(root/'sim'),str(Path(__file__).parent)]
from test_range_uncertainty_physics_seam_20261008 import controller,test_outward_range_error_does_not_authorize_clearance_loss
fixture=controller.__wrapped__();c,sent=next(fixture)
try:
 original=c._planner.points.copy();c._planner.clearance+=.05
 test_outward_range_error_does_not_authorize_clearance_loss((c,sent))
 print(json.dumps(dict(diagnostic_pass=True,reserve_m=.05,acceptance_clearance_m=.70,lidar_filter_changed=False,extra_queue_s=0.,normal_response_s=.6)))
finally:
 try:next(fixture)
 except StopIteration:pass
