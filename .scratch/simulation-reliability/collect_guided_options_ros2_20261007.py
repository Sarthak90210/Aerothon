"""Read only live MAVROS ROS2 FCU-parameter cache, without setting anything."""
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
from rcl_interfaces.msg import ParameterType
from rcl_interfaces.srv import GetParameters
from mavros_msgs.msg import State
from rosidl_runtime_py.convert import message_to_ordereddict


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--timeout',type=float,default=30.)
    p.add_argument('--parameter',default='GUID_OPTIONS')
    args=p.parse_args()
    if not 0<args.timeout<=60:p.error('timeout must be in (0,60] seconds')
    if args.out.exists():p.error('Preserve prior observation: output already exists')
    rclpy.init()
    node=Node('sitl_guided_options_ros2_observer',parameter_overrides=[Parameter('use_sim_time',value=True)])
    flight=[]
    def observe(msg):
        flight.append(dict(received_sim_stamp=node.get_clock().now().nanoseconds*1e-9,
            received_wall_s=time.monotonic(),data=message_to_ordereddict(msg)))
        del flight[:-4]
    node.create_subscription(State,'/mavros/state',observe,qos_profile_sensor_data)
    service='/mavros/param/get_parameters'
    client=node.create_client(GetParameters,service)
    began=time.monotonic();future=None;response=None;failure=None
    report=dict(kind='read-only actual-SITL MAVROS FCU parameter cache observation',service=service,
        ros_domain=os.environ.get('ROS_DOMAIN_ID'),parameter=args.parameter,
        source='MAVROS ROS2 GetParameters reply; not a synchronous FCU PARAM_VALUE transaction',
        hardware_qualified=False,qualified_parameter_observation=False)
    try:
        while time.monotonic()-began<args.timeout:
            rclpy.spin_once(node,timeout_sec=.1)
            if future is None and client.service_is_ready() and flight and flight[-1]['data']['connected']:
                req=GetParameters.Request();req.names=[args.parameter]
                report['requested_sim_stamp']=node.get_clock().now().nanoseconds*1e-9
                report['requested_wall_s']=time.monotonic();future=client.call_async(req)
            if future is not None and future.done():
                try:response=future.result()
                except Exception as exc:failure=repr(exc)
                break
        report['observed_sim_stamp']=node.get_clock().now().nanoseconds*1e-9
        report['observed_wall_s']=time.monotonic()
        report['flight_observations']=flight
        report['advertised_parameter_read_services']=[dict(name=n,types=t) for n,t in node.get_service_names_and_types()
            if n.startswith('/mavros/param/') and ('get' in n or 'pull' in n)]
        report['response']=message_to_ordereddict(response) if response is not None else None
        raw=None
        if response is not None and len(response.values)==1:
            v=response.values[0]
            if v.type==ParameterType.PARAMETER_INTEGER:raw=v.integer_value
            elif v.type==ParameterType.PARAMETER_DOUBLE:raw=v.double_value
        if raw is not None and math.isfinite(raw) and 0<=raw<2**32 and abs(raw-round(raw))<1e-6:
            value=int(round(raw));report['qualified_parameter_observation']=True;report['value']=value
            report['position_stabilization_enabled']=not bool(value & (1<<4))
            report['velocity_stabilization_enabled']=not bool(value & (1<<5))
            report['wpnav_for_position_enabled']=bool(value & (1<<6))
        else:report['reason']=failure or f'No valid integer-valued {args.parameter} in connected MAVROS ROS2 cache reply'
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open('x') as f:f.write(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:
        node.destroy_node();rclpy.try_shutdown()
    return 0 if report['qualified_parameter_observation'] else 1


if __name__=='__main__':raise SystemExit(main())
