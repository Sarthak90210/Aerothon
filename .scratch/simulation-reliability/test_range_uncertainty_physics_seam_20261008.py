"""Normal packet/airframe must preserve .70 m with outward range error."""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
import copy
from rclpy.parameter import Parameter
from test_corridor_clearance_contract import controller
from test_local_planner import wall_scan
from test_headless_land_position_hold import world,DT

def test_outward_range_error_does_not_authorize_clearance_loss(controller):
 c,sent=controller;c.set_parameters([Parameter('motion_computation_budget_s',value=.20)])
 # Recorded V30 observed clearance .728996 while truth was .690823,
 # a 38 mm discrepancy. Probe 40 mm without changing/filtering returns.
 observed=.78;true_gap=observed-.04
 c._planner.observe(*wall_scan(observed,1.75));c._compensated=lambda vx,vy:(0.,.08)
 c._publish(0.,0.,2.,0.,{})
 w=world();w.p[:2]=0.;w.v[:]=0.;w.wind=lambda t:(0.,0.)
 w._on_sp_raw(sent[-1]);closest=true_gap
 for _ in range(round(.6/DT)):
  w.t+=DT;w._step_airframe();closest=min(closest,true_gap-w.p[1])
 stop=copy.deepcopy(sent[-1]);stop.velocity.x=stop.velocity.y=0.;w._on_sp_raw(stop)
 for _ in range(round(3.6/DT)):
  w.t+=DT;w._step_airframe();closest=min(closest,true_gap-w.p[1])
 print(dict(closest=closest,issued_left=sent[-1].velocity.y,normal_response_s=w.args.vel_response_s,extra_queue_s=w.args.vel_command_delay_s))
 assert closest>=.70
