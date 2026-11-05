"""One read-only query of the existing live MAVROS FCU parameter cache."""
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

NAMES=['GUID_OPTIONS','PSC_VELXY_P','PSC_VELXY_I','PSC_VELXY_D','PSC_VELXY_FF',
       'PSC_POSXY_P','WPNAV_ACCEL','WPNAV_SPEED','GUID_TIMEOUT']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():parser.error('Preserve existing observation')
    rclpy.init()
    node=Node('sitl_control_parameter_observer',parameter_overrides=[Parameter('use_sim_time',value=True)])
    flight=[]
    def observe(msg):
        flight.append(dict(received_sim_stamp=node.get_clock().now().nanoseconds*1e-9,
            received_wall_s=time.monotonic(),data=message_to_ordereddict(msg)))
        del flight[:-4]
    node.create_subscription(State,'/mavros/state',observe,qos_profile_sensor_data)
    service='/mavros/param/get_parameters';client=node.create_client(GetParameters,service)
    future=None;response=None;failure=None;began=time.monotonic()
    report=dict(kind='read-only live actual-SITL control parameter cache observation',service=service,
        ros_domain=os.environ.get('ROS_DOMAIN_ID'),requested_names=NAMES,
        source='One MAVROS ROS2 GetParameters request; no list pull, PARAM_SET, control, arming or hardware query')
    try:
        while time.monotonic()-began<30:
            rclpy.spin_once(node,timeout_sec=.1)
            if future is None and client.service_is_ready() and flight and flight[-1]['data']['connected']:
                req=GetParameters.Request();req.names=NAMES
                report['requested_sim_stamp']=node.get_clock().now().nanoseconds*1e-9
                report['requested_wall_s']=time.monotonic();future=client.call_async(req)
            if future is not None and future.done():
                try:response=future.result()
                except Exception as exc:failure=repr(exc)
                break
        report['observed_sim_stamp']=node.get_clock().now().nanoseconds*1e-9
        report['observed_wall_s']=time.monotonic();report['flight_observations']=flight
        report['response']=message_to_ordereddict(response) if response is not None else None
        values=response.values if response is not None else []
        decoded={}
        for i,name in enumerate(NAMES):
            value=None;kind=None
            if i<len(values):
                v=values[i];kind=v.type
                if kind==ParameterType.PARAMETER_INTEGER:value=v.integer_value
                elif kind==ParameterType.PARAMETER_DOUBLE:value=v.double_value
            valid=value is not None and math.isfinite(value)
            decoded[name]=dict(available=valid,type=kind,value=value if valid else None,
                reason=None if valid else failure or 'Missing or unsupported typed cache value; no default inferred')
        report['parameters']=decoded
        report['all_parameters_available']=all(v['available'] for v in decoded.values())
        report['limits']=['Typed live MAVROS cache replies are observations of cached FCU parameters, not synchronous MAVLink PARAM_VALUE reads.',
                          'Parameter values alone do not identify delay, bandwidth, hold robustness or a qualified disturbance envelope.',
                          'Existing failed narrow-gust and headless grades remain failures. Hardware remains unqualified.']
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open('x') as f:f.write(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:node.destroy_node();rclpy.try_shutdown()
    return 0 if report['all_parameters_available'] else 1


if __name__=='__main__':raise SystemExit(main())
