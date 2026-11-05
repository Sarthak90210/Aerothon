"""Read FC parameters through MAVROS in one request; prints name = value.

    python3 /home/aerothon/state/deploy_20261025/fc_params.py RC6_OPTION TUNE ...
"""
import sys

import rclpy
from rcl_interfaces.srv import GetParameters

rclpy.init()
node = rclpy.create_node('fc_params')
client = node.create_client(GetParameters, '/mavros/param/get_parameters')
if not client.wait_for_service(timeout_sec=20):
    sys.exit('no /mavros/param/get_parameters service')
names = sys.argv[1:]
future = client.call_async(GetParameters.Request(names=names))
rclpy.spin_until_future_complete(node, future, timeout_sec=60)
if not future.done():
    sys.exit('no reply in 60 s')
for name, value in zip(names, future.result().values):
    shown = {1: value.bool_value, 2: value.integer_value, 3: value.double_value}.get(value.type, 'not set')
    print(f'{name} = {shown}', flush=True)
