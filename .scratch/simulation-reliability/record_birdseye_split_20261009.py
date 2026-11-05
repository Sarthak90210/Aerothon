"""Passive native overhead camera recording, independent of ROS/controller inputs."""
import argparse
import json
import queue
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from gz.transport13 import Node
from gz.msgs10.boolean_pb2 import Boolean
from gz.msgs10.entity_factory_pb2 import EntityFactory
from gz.msgs10.image_pb2 import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--mission', type=Path, required=True)
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=False)
frames = args.out / 'frames'
frames.mkdir()
topic = '/evaluation/birdseye/image'
camera_sdf = '''<sdf version="1.9"><model name="evaluation_birdseye_camera">
<static>true</static><pose>24.25 -4.8 90 0 1.5707963267948966 1.5707963267948966</pose>
<link name="camera_link"><sensor name="overhead" type="camera">
<always_on>true</always_on><update_rate>3</update_rate><topic>/evaluation/birdseye/image</topic>
<camera><horizontal_fov>0.84</horizontal_fov><image><width>1600</width><height>1200</height><format>R8G8B8</format></image>
<clip><near>0.1</near><far>250</far></clip></camera>
</sensor></link></model></sdf>'''
(args.out / 'camera.sdf').write_text(camera_sdf)
(args.out / 'configuration.json').write_text(json.dumps(dict(
    view='fixed bird-eye native Gazebo camera', topic=topic, world='split_corridors.json',
    pose=[24.25,-4.8,90,0,1.5707963267948966,1.5707963267948966],
    horizontal_fov_rad=.84, width=1600, height=1200, update_rate_hz=3,
    ros_publications=False, controller_source_modified=False, qualification='user-requested recording; qualification paused'), indent=2))
native = Node()
started = time.monotonic()
spawned = False
request = EntityFactory(sdf=camera_sdf, name='evaluation_birdseye_camera', allow_renaming=False)
while time.monotonic() - started < 900:
    ok, response = native.request('/world/mission2/create', request, EntityFactory, Boolean, 1000)
    if ok and response.data:
        spawned = True
        break
    time.sleep(2)
if not spawned:
    raise SystemExit('Overhead camera could not be spawned; mission must not start')
pending = queue.Queue(maxsize=8)
closing = threading.Event()
stats = dict(received=0, dropped=0, written=0)
def receive(message):
    if closing.is_set():
        return
    stats['received'] += 1
    stamp = message.header.stamp.sec + message.header.stamp.nsec * 1e-9
    item = (stamp, message.width, message.height, message.step,
            message.pixel_format_type, bytes(message.data))
    try:
        pending.put_nowait(item)
    except queue.Full:
        stats['dropped'] += 1
if not native.subscribe(Image, topic, receive):
    raise SystemExit('Overhead camera subscription failed')
ledger = (args.out / 'frames.jsonl').open('x')
last_stamp = None
last_receive = time.monotonic()
try:
    while time.monotonic() - started < 7200:
        try:
            stamp, width, height, step, pixel_format, data = pending.get(timeout=.5)
        except queue.Empty:
            if (args.mission / 'recorded_result.json').exists() and time.monotonic() - last_receive > 2:
                break
            continue
        last_receive = time.monotonic()
        if stamp == last_stamp:
            continue
        last_stamp = stamp
        # The configured R8G8B8 sensor emits RGB bytes, preserving row padding.
        array = np.frombuffer(data, np.uint8).reshape(height, step)[:, :width*3].reshape(height,width,3)
        bgr = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
        name = f'frame_{stats["written"]:06d}.jpg'
        if not cv2.imwrite(str(frames / name), bgr, [cv2.IMWRITE_JPEG_QUALITY, 92]):
            raise RuntimeError('Overhead frame write failed')
        ledger.write(json.dumps(dict(index=stats['written'], stamp=stamp, file='frames/'+name,
            width=width, height=height, pixel_format=int(pixel_format)))+'\n')
        ledger.flush()
        stats['written'] += 1
        if stats['written'] == 1:
            cv2.imwrite(str(args.out / 'preview.png'), bgr)
            (args.out / 'ready.json').write_text(json.dumps(dict(stamp=stamp, topic=topic, width=width, height=height)))
            print('Overhead native camera ready at '+str(stamp), flush=True)
        if (args.mission / 'recorded_result.json').exists():
            break
finally:
    closing.set()
    native.unsubscribe(topic)
    time.sleep(.2)
    ledger.close()
    (args.out / 'capture_summary.json').write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats), flush=True)

