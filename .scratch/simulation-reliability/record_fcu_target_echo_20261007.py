"""Record FCU target echoes to distinguish transport and velocity response.
Requests telemetry message 85 only; does not write parameters or flight targets.
"""
import argparse,hashlib,json,time
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from mavros_msgs.msg import PositionTarget,State
from mavros_msgs.srv import CommandLong
from geometry_msgs.msg import PoseStamped,TwistStamped
from rosidl_runtime_py.convert import message_to_ordereddict
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
end=time.monotonic()+1800
while not args.out.exists() and time.monotonic()<end:time.sleep(.1)
if not args.out.exists():raise SystemExit('Owned run output never appeared')
source=Path(__file__).read_bytes();(args.out/'target_echo_recorder_source.py').write_bytes(source)
rclpy.init();node=Node('fcu_target_echo_observer',parameter_overrides=[Parameter('use_sim_time',value=True)])
state=[None];counts={};request={}
stream=(args.out/'fcu_target_echo_observations.jsonl').open('x')
def capture(topic,msg):
    counts[topic]=counts.get(topic,0)+1
    stream.write(json.dumps(dict(received_stamp=node.get_clock().now().nanoseconds*1e-9,
        wall_monotonic_s=time.monotonic(),topic=topic,data=message_to_ordereddict(msg)))+'\n');stream.flush()
for topic,typ in [('/mavros/setpoint_raw/target_local',PositionTarget),
        ('/mavros/setpoint_raw/local',PositionTarget),('/mavros/local_position/pose',PoseStamped),
        ('/mavros/local_position/velocity_local',TwistStamped)]:
    node.create_subscription(typ,topic,lambda m,t=topic:capture(t,m),qos_profile_sensor_data)
node.create_subscription(State,'/mavros/state',lambda m:state.__setitem__(0,m),10)
client=node.create_client(CommandLong,'/mavros/cmd/command')
try:
    while time.monotonic()<end and (state[0] is None or not state[0].connected):rclpy.spin_once(node,timeout_sec=.1)
    if state[0] is None or not state[0].connected:raise RuntimeError('FCU did not connect')
    if not client.wait_for_service(timeout_sec=30.):raise RuntimeError('Telemetry interval service absent')
    req=CommandLong.Request();req.command=511;req.param1=85.;req.param2=50000.
    future=client.call_async(req);deadline=time.monotonic()+10.
    while not future.done() and time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.1)
    accepted=future.done() and future.result() is not None and future.result().success
    request=dict(command=511,message_id=85,interval_us=50000,accepted=bool(accepted))
    if not accepted:raise RuntimeError('FCU rejected target-echo telemetry request')
    while time.monotonic()<end and not (args.out/'recorded_result.json').exists():rclpy.spin_once(node,timeout_sec=.1)
finally:
    stream.close();node.destroy_node();rclpy.try_shutdown()
    with (args.out/'fcu_target_echo_recorder_summary.json').open('x') as f:json.dump(dict(
        scope='Diagnostic onboard command/target/pose/velocity observation only',
        source_sha256=hashlib.sha256(source).hexdigest(),request=request,counts=counts,
        controller_inputs_changed=False,parameters_or_flight_targets_written=False),f,indent=2)
