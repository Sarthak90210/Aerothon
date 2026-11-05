"""Read the isolated simulation ROS graph; no topic or service publications."""
import json
import sys
import time
from pathlib import Path
import rclpy
from std_msgs.msg import String

rclpy.init()
node=rclpy.create_node('decision_input_audit')
arguments=list(sys.argv[2:])
wait_navigation='--wait-navigation' in arguments
wait_delivery='--wait-delivery' in arguments
arguments=[a for a in arguments if a not in ('--wait-navigation','--wait-delivery')]
required=tuple(arguments) or ('mission_bt','winch_ctrl','velocity_controller')
until=time.monotonic()+60
graph={}
activation={}
try:
    if wait_navigation or wait_delivery:
        def observe(message):
            try:detail=json.loads(message.data)
            except ValueError:return
            active=(detail.get('planner_state') and detail.get('state')!='OBSERVING') if wait_navigation else detail.get('state') in ('BASELINE','ACQUIRE','LOWER','PROBE','CANDIDATE_PROBE','PROBE_HOLD','STOW','FINAL','RECOVER_STOW')
            if active:
                activation.update(detail)
        topic='/avoidance/detail' if wait_navigation else '/mission/delivery_observation'
        node.create_subscription(String,topic,observe,10)
        until=time.monotonic()+2400
        while time.monotonic()<until and not activation:
            rclpy.spin_once(node,timeout_sec=.1)
        until=time.monotonic()+60
    while time.monotonic()<until:
        rclpy.spin_once(node,timeout_sec=.1)
        graph={name:node.get_subscriber_names_and_types_by_node(name,'/')
               for name in required if name in node.get_node_names()}
        if all(graph.get(name) for name in required):break
    forbidden=[(name,topic) for name,topics in graph.items() for topic,_ in topics
               if topic.startswith('/sim/') or topic in ('/tf','/odometry')
               or any(s in topic for s in ('contact','attachment','detach'))]
    result=dict(nodes=graph,missing_nodes=[n for n in required if not graph.get(n)],
                navigation_activation=activation if wait_navigation else None,
                delivery_activation=activation if wait_delivery else None,
                forbidden_subscriptions=forbidden,
                observation='live ROS graph; native release component has no ROS interface',
                scope='direct decision-node subscriptions including dynamic TF/native odometry; static equipment mounts, image/lidar/FCU telemetry are allowed')
    result['pass']=not result['missing_nodes'] and not forbidden and (bool(activation) or not (wait_navigation or wait_delivery))
    path=Path(sys.argv[1])
    if path.exists():raise SystemExit('Audit output already exists; original evidence preserved')
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
finally:
    node.destroy_node()
    rclpy.try_shutdown()
raise SystemExit(0 if result['pass'] else 1)
