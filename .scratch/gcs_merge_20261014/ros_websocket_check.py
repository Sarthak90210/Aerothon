"""Isolated typed ROS/WebSocket check. No FCU, mission or actuator nodes."""
import asyncio
import json
import os
import threading
import time
from pathlib import Path

os.environ['AEROTHON_GCS_WS_PORT'] = '18765'
os.environ['ROS_DOMAIN_ID'] = '196'
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from mavros_msgs.msg import State, Vibration
from sensor_msgs.msg import MagneticField, BatteryState, Image, LaserScan
from std_msgs.msg import String, Bool
from gcs_aggregator.aggregator import Aggregator, TEST_PARTS
import websockets

root = Path(__file__).resolve().parents[2]
results = {'scope':'isolated typed ROS and WebSocket contract; no FCU/SITL/Gazebo or physical actuation', 'checks':[]}
rclpy.init(args=['--ros-args', '-p', f'dimension_presets_file:={root}/.scratch/gcs_merge_20261014/loopback-presets.json'])
aggregator = Aggregator()
fixture = Node('gcs_isolated_contract_fixture')
observed = {'parts':[], 'start':[], 'winch':[], 'dimensions':[]}
for key, topic, cls in [('parts','/mission/test_part',String),('start','/mission/start',Bool),('winch','/winch/cmd',String),('dimensions','/mission/arena_dimensions',String)]:
    fixture.create_subscription(cls, topic, lambda m, key=key: observed[key].append(m.data), 10)
publishers = [(cls, fixture.create_publisher(cls, topic, qos_profile_sensor_data)) for cls,topic in [(State,'/mavros/state'),(Vibration,'/mavros/vibration/raw/vibration'),(MagneticField,'/mavros/imu/mag'),(BatteryState,'/mavros/battery'),(Image,'/image_raw'),(LaserScan,'/scan')]]
phase = fixture.create_publisher(String, '/mission/state', 10)
ready = fixture.create_publisher(Bool, '/mission_ready', 10)
def publish():
    for cls, pub in publishers:
        m = cls()
        if hasattr(m,'header'): m.header.stamp = fixture.get_clock().now().to_msg(); m.header.frame_id = 'base_link'
        if cls is State: m.connected=True; m.armed=False; m.mode='GUIDED'
        elif cls is Vibration: m.vibration.x=2.; m.vibration.y=3.; m.vibration.z=4.
        elif cls is MagneticField: m.magnetic_field.x=30e-6; m.magnetic_field.y=40e-6
        elif cls is BatteryState: m.voltage=16.; m.percentage=.8; m.current=4.
        elif cls is Image: m.width=1; m.height=1; m.encoding='mono8'; m.step=1; m.data=[0]
        elif cls is LaserScan: m.range_min=.05; m.range_max=12.; m.angle_increment=.1; m.ranges=[2.,3.,4.]
        pub.publish(m)
    ready.publish(Bool(data=True))
timer = fixture.create_timer(.1,publish)
executor = SingleThreadedExecutor(); executor.add_node(aggregator); executor.add_node(fixture)
spin = threading.Thread(target=executor.spin,daemon=True); spin.start(); aggregator.start_ws()

async def receive(ws, kind, cid=None):
    async with asyncio.timeout(5):
        while True:
            e = json.loads(await ws.recv())
            if e['kind']==kind and (cid is None or e['data'].get('cmd_id')==cid): return e['data']

async def request(ws, cid, cmd, args):
    await ws.send(json.dumps({'v':1,'kind':'command','data':{'cmd_id':cid,'cmd':cmd,'args':args,'confirm':True}}))
    return await receive(ws,'ack',cid)

async def check():
    await asyncio.sleep(1)
    async with websockets.connect('ws://127.0.0.1:18765') as ws:
        t = await receive(ws,'telemetry')
        assert t['safety']['fcu_connected'] and t['sample_age_s']['state'] < 1
        assert t['sensor_diagnostics']['clipping']==[0.,0.,0.]
        assert abs(t['sensor_diagnostics']['magnetic_strength_ut']-50)<1e-6
        assert t['devices']['camera']['hz']>5 and t['devices']['lidar']['capture_age_s']<1
        results['checks'].append('real typed ROS sensor callbacks and websocket serialization')
        results['sensor_snapshot'] = t
        from mission_bt.arena_dimensions import defaults
        assert (await request(ws,'dimensions','set_arena_dimensions',{'dimensions':defaults()}))['result']=='accepted'
        for part in TEST_PARTS:
            phase.publish(String(data='WAITING')); await asyncio.sleep(.2)
            cmd = 'start_mission' if part=='mission' else 'start_test'
            assert (await request(ws,part,cmd,{} if part=='mission' else {'part':part}))['result']=='accepted'
            await asyncio.sleep(.1)
            assert part in observed['parts']
        results['checks'].append('all six production mission/test parts dispatch through existing ROS topics')
        assert (await request(ws,'parallel','start_test',{'part':'search'}))['result']=='rejected'
        results['checks'].append('concurrent execution rejected')
        assert (await request(ws,'release-once','winch',{'action':'release'}))['result']=='accepted'
    async with websockets.connect('ws://127.0.0.1:18765') as ws:
        assert (await request(ws,'release-once','winch',{'action':'release'}))['result']=='accepted'
        await asyncio.sleep(.2)
        assert observed['winch'].count('release')==1
        results['checks'].append('reconnect does not repeat the same release command ID')
        fixture.destroy_timer(timer)
        await asyncio.sleep(3.3)
        # Skip snapshots already queued while the publisher was alive.
        while True:
            stale = await receive(ws,'telemetry')
            if stale['sample_age_s']['state'] >= 3: break
        assert stale['devices']['camera']['ok'] is False
        results['checks'].append('stopped sensor and FCU publishers become explicitly stale')
    results['observed'] = observed

try:
    asyncio.run(check()); results['passed']=True
finally:
    executor.shutdown(); spin.join(timeout=2); aggregator.destroy_node(); fixture.destroy_node(); rclpy.shutdown()
    (root/'.scratch/gcs_merge_20261014/ros-websocket-result.json').write_text(json.dumps(results,indent=2))
print(json.dumps({'passed':results['passed'],'checks':results['checks']},indent=2))
