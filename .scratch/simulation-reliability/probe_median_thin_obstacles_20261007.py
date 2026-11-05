"""Check real lidar conditioning against ray-cast thin obstacle observations."""
import hashlib
import json
import math
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
snapshot = root/'.scratch/command_deadline_candidate_20261007'
sys.path.insert(0, str(snapshot/'src/aerothon_avoidance/avoidance'))
from avoidance import velocity_controller
assert Path(velocity_controller.__file__).resolve().is_relative_to(snapshot.resolve())
sys.path.insert(0, str(snapshot/'sim'))
import test_slalom_traverse as slalom
import rclpy
from rclpy.parameter import Parameter

rclpy.init()
node = velocity_controller.VelocityController()
rows = []
try:
    for width in (.1, .2, .4):
        for distance in (2., 4., 8.):
            for phase in (0., .25, .5, .75):
                yaw = phase*2*math.pi/slalom.N_BEAMS
                scan = slalom.scan_at(0., 0., yaw, [slalom.rect(distance, 0., .1, width)])
                raw_hits = sum(value < 11. for value in scan.ranges)
                processed = {}
                for window in (3, 5):
                    node.set_parameters([Parameter('median_window', value=window)])
                    _, ranges = node.conditioned(scan)
                    processed[str(window)] = int(sum(ranges < 11.))
                rows.append(dict(width_m=width, distance_m=distance, beam_phase=phase,
                    raw_hits=raw_hits, processed_hits=processed))
finally:
    node.destroy_node()
    rclpy.shutdown()
report = dict(rows=rows, tests=len(rows), production_modified=False,
    source_sha256=hashlib.sha256(Path(velocity_controller.__file__).read_bytes()).hexdigest(),
    loses_existing_obstacle_detection=[row for row in rows if row['processed_hits']['3'] and not row['processed_hits']['5']],
    scope='Controlled sensor-conditioning diagnostic, not flight qualification; geometry generates test observations only')
out = root/'logs/reliability_median_thin_obstacles_20261007.json'
with out.open('x') as stream:
    json.dump(report, stream, indent=2)
print(json.dumps(dict(tests=len(rows), wider_filter_regressions=len(report['loses_existing_obstacle_detection']))))
raise SystemExit(1 if report['loses_existing_obstacle_detection'] else 0)
