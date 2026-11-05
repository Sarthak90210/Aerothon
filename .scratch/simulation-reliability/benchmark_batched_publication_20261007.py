"""Measure actual publication code on identical fresh scans and fixed captures."""
import json
import sys
import time
from pathlib import Path
from types import MethodType
import numpy as np
root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/command_deadline_candidate_20261007'
sys.path[:0]=[str(snapshot/'src/aerothon_avoidance/avoidance'),str(root/'sim')]
import rclpy
from rclpy.parameter import Parameter
from sensor_msgs.msg import LaserScan
from avoidance.velocity_controller import VelocityController
from test_local_planner import wall_scan
from batched_certificate_candidate_20261007 import install
out=root/'logs/reliability_batched_publication_benchmark_20261007';out.mkdir(exist_ok=False)
original=VelocityController._publish
install(VelocityController,out/'source_override')
candidate=VelocityController._publish
rclpy.init();node=VelocityController()
node.set_parameters([Parameter('motion_computation_budget_s',value=0.),Parameter('vel_command_delay_s',value=.4)])
node._now=lambda:1.;node._pose_t=node._scan_t=1.
node.scan=LaserScan();node._compensated=lambda vx,vy:(vx,vy)
node._ground_world=np.array([0.,.25]);node._wind_world=np.array([0.,.35])
node._pos=(0.,0.);node._yaw=0.;node._planner.observe(*wall_scan(.8,1.75))
commands=[];node.pub_sp.publish=commands.append
results=[]
try:
    for label,method in [('original',original),('batched',candidate)]:
        timings=[];emitted=[]
        node._publish=MethodType(method,node)
        for _ in range(30):
            node._command_history.clear();node._yaw_command_history.clear();node._sent_heading.clear()
            start=time.perf_counter();node._publish(.8,.4,2.,0.,{});timings.append(time.perf_counter()-start)
            sp=commands[-1];emitted.append([sp.velocity.x,sp.velocity.y,sp.yaw_rate])
        results.append(dict(variant=label,seconds=timings,median_s=float(np.median(timings)),commands=emitted))
    assert results[0]['commands']==results[1]['commands']
    report=dict(results=results,identical_emitted_commands=True,median_speedup=results[0]['median_s']/results[1]['median_s'],
        scope='Host timing microbenchmark on same controller state; not rendered or flight qualification',production_modified=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(original_median_s=results[0]['median_s'],batched_median_s=results[1]['median_s'],speedup=report['median_speedup'])))
finally:node.destroy_node();rclpy.shutdown()
