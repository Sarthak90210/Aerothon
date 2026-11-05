"""Real ROS clock callbacks during a blocked planner-sized timer callback."""
import hashlib,json,threading,time
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.executors import SingleThreadedExecutor
from rosgraph_msgs.msg import Clock
from independent_ros_clock_candidate_20261007 import IndependentRosClock

rclpy.init()
publisher=Node('controlled_clock_publisher',use_global_arguments=False)
pub=publisher.create_publisher(Clock,'/clock',10)
stop=threading.Event()
def publish():
    t=10.
    while not stop.wait(.01):
        t+=.04
        msg=Clock();msg.clock.sec=int(t);msg.clock.nanosec=round((t-int(t))*1e9)
        pub.publish(msg)
thread=threading.Thread(target=publish,daemon=True);thread.start()
results=[]
try:
    for independent in (False,True):
        node=Node('clock_block_probe_'+str(independent),use_global_arguments=False,
            parameter_overrides=[Parameter('use_sim_time',value=True)])
        driver=IndependentRosClock(node) if independent else None
        executor=SingleThreadedExecutor();executor.add_node(node)
        done=[]
        def blocked_callback():
            timer.cancel()
            begin=node.get_clock().now().nanoseconds*1e-9
            before=time.monotonic()
            time.sleep(.3)
            end=node.get_clock().now().nanoseconds*1e-9
            done.append(dict(independent_clock=independent,
                begin_sim_s=begin,end_sim_s=end,observed_capture_age_s=end-begin,
                callback_host_s=time.monotonic()-before))
        timer=node.create_timer(.1,blocked_callback)
        until=time.monotonic()+5.
        while not done and time.monotonic()<until:executor.spin_once(timeout_sec=.1)
        assert done,'Clock probe timer did not execute'
        results+=done
        executor.shutdown()
        if driver:driver.close()
        node.destroy_node()
    assert results[0]['observed_capture_age_s']==0.
    assert results[1]['observed_capture_age_s']>=.7
    out=Path('logs/reliability_independent_ros_clock_candidate_20261007.json')
    with out.open('x') as handle:json.dump(dict(scope='ROS integration timing only; no flight qualification',
        rows=results,simulator_geometry_or_contact_input=False,
        source_sha256=hashlib.sha256(Path(__file__).with_name('independent_ros_clock_candidate_20261007.py').read_bytes()).hexdigest()),handle,indent=2)
    print(json.dumps(results))
finally:
    stop.set();thread.join(timeout=2.)
    publisher.destroy_node();rclpy.shutdown()
