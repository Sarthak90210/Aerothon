"""Read-only MAVROS ParamGet observation; parent starts it with actual SITL."""
import argparse
import json
import math
import os
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from mavros_msgs.msg import State
from mavros_msgs.srv import ParamGet
from rosidl_runtime_py.convert import message_to_ordereddict


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--service',default='/mavros/param/get')
    p.add_argument('--timeout',type=float,default=30.)
    args=p.parse_args()
    if not 0<args.timeout<=60:p.error('timeout must be in (0,60] seconds')
    if args.out.exists():p.error('Preserve prior observation: output already exists')
    rclpy.init()
    node=Node('sitl_guided_options_observer',parameter_overrides=[Parameter('use_sim_time',value=True)])
    flight=[]
    def observe(msg):
        flight.append(dict(received_sim_stamp=node.get_clock().now().nanoseconds*1e-9,
            received_wall_s=time.monotonic(),data=message_to_ordereddict(msg)))
        del flight[:-4]
    node.create_subscription(State,'/mavros/state',observe,qos_profile_sensor_data)
    client=node.create_client(ParamGet,args.service)
    began=time.monotonic();future=None;response=None;failure=None
    report=dict(kind='read-only actual-SITL parameter observation',service=args.service,
        ros_domain=os.environ.get('ROS_DOMAIN_ID'),parameter='GUIDED_OPTIONS',
        source='MAVROS ParamGet reply; no parameter set, control or arming request',
        hardware_qualified=False)
    try:
        while time.monotonic()-began<args.timeout:
            rclpy.spin_once(node,timeout_sec=.1)
            if future is None and client.service_is_ready() and flight and flight[-1]['data']['connected']:
                request=ParamGet.Request();request.param_id='GUIDED_OPTIONS'
                report['requested_sim_stamp']=node.get_clock().now().nanoseconds*1e-9
                report['requested_wall_s']=time.monotonic()
                future=client.call_async(request)
            if future is not None and future.done():
                try:response=future.result()
                except Exception as exc:failure=repr(exc)
                break
        report['observed_sim_stamp']=node.get_clock().now().nanoseconds*1e-9
        report['observed_wall_s']=time.monotonic()
        report['flight_observations']=flight
        report['response']=message_to_ordereddict(response) if response is not None else None
        if response is None:
            report['qualified_parameter_observation']=False
            report['reason']=failure or 'No connected ParamGet reply before timeout; do not infer GUIDED_OPTIONS'
        elif not response.success:
            report['qualified_parameter_observation']=False
            report['reason']='FCU parameter query was unsuccessful'
        else:
            # ParamValue documents both fields zero as the valid value zero.
            raw=response.value.integer if response.value.integer!=0 else response.value.real
            valid=math.isfinite(raw) and 0<=raw<2**32 and abs(raw-round(raw))<1e-6
            report['qualified_parameter_observation']=bool(valid)
            if valid:
                value=int(round(raw));report['value']=value
                report['position_stabilization_enabled']=not bool(value & (1<<4))
                report['velocity_stabilization_enabled']=not bool(value & (1<<5))
                report['wpnav_for_position_enabled']=bool(value & (1<<6))
            else:report['reason']='Returned GUIDED_OPTIONS is not a valid integer mask'
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open('x') as f:f.write(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:
        node.destroy_node();rclpy.try_shutdown()
    return 0 if report['qualified_parameter_observation'] else 1


if __name__=='__main__':raise SystemExit(main())
