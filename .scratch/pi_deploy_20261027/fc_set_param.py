"""Set one integer FC parameter through MAVROS, refusing while armed; prints the result.

    python3 /home/aerothon/state/deploy_20261027/fc_set_param.py SERVO5_FUNCTION 7
"""
import sys

import rclpy
from mavros_msgs.msg import State
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import SetParameters

name, value = sys.argv[1], int(sys.argv[2])
rclpy.init()
node = rclpy.create_node('fc_set_param')
state = {}
node.create_subscription(State, '/mavros/state', lambda m: state.update(armed=m.armed, connected=m.connected), 10)
deadline = node.get_clock().now().nanoseconds + 10e9
while 'armed' not in state and node.get_clock().now().nanoseconds < deadline:
    rclpy.spin_once(node, timeout_sec=0.2)
if state.get('connected') is not True or state.get('armed') is not False:
    sys.exit(f'refusing: FCU state {state or "unknown"} (needs connected and disarmed)')
client = node.create_client(SetParameters, '/mavros/param/set_parameters')
if not client.wait_for_service(timeout_sec=20):
    sys.exit('no /mavros/param/set_parameters service')
request = SetParameters.Request(parameters=[Parameter(
    name=name, value=ParameterValue(type=ParameterType.PARAMETER_INTEGER, integer_value=value))])
future = client.call_async(request)
rclpy.spin_until_future_complete(node, future, timeout_sec=60)
if not future.done():
    sys.exit('no reply in 60 s')
result = future.result().results[0]
print(f'{name} = {value}: successful={result.successful} {result.reason}', flush=True)
