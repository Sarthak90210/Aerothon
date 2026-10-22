#!/usr/bin/env python3
"""Record a native Gazebo camera that FOLLOWS the aircraft. Evaluation only.

A static camera model with no visual or collision (invisible to the
aircraft's lidar and camera; nothing is published to ROS) is re-posed behind
and above the aircraft from the simulator's true pose
(/world/<world>/dynamic_pose/info), looking at it. Its heading follows the
aircraft's smoothed heading so yaw sweeps do not whip the view round.

Writes OUT/chase/: frames/*.jpg, frames.jsonl (sim stamp per frame),
configuration.json, capture_summary.json. Stops on Ctrl-C/SIGTERM, when
--stop-file exists, or after --max-s wall seconds. Encode with
sim/encode_chase.py.
"""
import argparse
import json
import math
from pathlib import Path
import queue
import signal
import threading
import time

import cv2
import numpy as np
from gz.transport13 import Node
from gz.msgs10.boolean_pb2 import Boolean
from gz.msgs10.entity_factory_pb2 import EntityFactory
from gz.msgs10.image_pb2 import Image
from gz.msgs10.pose_pb2 import Pose
from gz.msgs10.pose_v_pb2 import Pose_V

NAME = 'evaluation_chase_camera'


def yaw_of(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def wrap(a):
    return math.atan2(math.sin(a), math.cos(a))


def quat(roll, pitch, yaw):
    cr, sr = math.cos(roll / 2), math.sin(roll / 2)
    cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
    cy, sy = math.cos(yaw / 2), math.sin(yaw / 2)
    return (cr * cp * cy + sr * sp * sy, sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--world', default='mission2')
    ap.add_argument('--model', default='aerothon_iris')
    ap.add_argument('--width', type=int, default=1280)
    ap.add_argument('--height', type=int, default=720)
    ap.add_argument('--hz', type=float, default=10.0)
    ap.add_argument('--hfov', type=float, default=1.0)
    ap.add_argument('--back', type=float, default=4.0)
    ap.add_argument('--up', type=float, default=3.0)
    ap.add_argument('--heading-tau', type=float, default=2.5,
                    help='heading smoothing time constant, sim s')
    ap.add_argument('--stop-file', type=Path)
    ap.add_argument('--max-s', type=float, default=7200)
    args = ap.parse_args()

    out = args.out / 'chase'
    out.mkdir(parents=True, exist_ok=False)
    (out / 'frames').mkdir()
    topic = '/evaluation/chase/image'
    sdf = f'''<sdf version="1.9"><model name="{NAME}"><static>true</static>
<pose>0 0 10 0 0.6 0</pose><link name="camera_link">
<sensor name="chase" type="camera"><always_on>true</always_on>
<update_rate>{args.hz}</update_rate><topic>{topic}</topic>
<camera><horizontal_fov>{args.hfov}</horizontal_fov><image><width>{args.width}</width>
<height>{args.height}</height><format>R8G8B8</format></image>
<clip><near>0.1</near><far>200</far></clip></camera></sensor></link></model></sdf>'''
    (out / 'camera.sdf').write_text(sdf)
    (out / 'configuration.json').write_text(json.dumps(dict(
        view='native Gazebo chase camera following the TRUE aircraft pose',
        topic=topic, world=args.world, model=args.model, width=args.width,
        height=args.height, hfov_rad=args.hfov, capture_hz=args.hz,
        back_m=args.back, up_m=args.up, heading_tau_s=args.heading_tau,
        ros_publications=False, flight_input=False), indent=2))

    node = Node()
    ok, res = node.request(f'/world/{args.world}/create',
                           EntityFactory(sdf=sdf, name=NAME, allow_renaming=False),
                           EntityFactory, Boolean, 5000)
    if not ok or not res.data:
        raise SystemExit('chase camera could not be created')

    lock = threading.Lock()
    state = dict(pose=None, stamp=None)

    def on_pose(msg):
        for p in msg.pose:
            if p.name == args.model:
                with lock:
                    state['pose'] = ((p.position.x, p.position.y, p.position.z), yaw_of(p.orientation))
                    state['stamp'] = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
                return

    if not node.subscribe(Pose_V, f'/world/{args.world}/dynamic_pose/info', on_pose):
        raise SystemExit('pose subscription failed')

    pending = queue.Queue(maxsize=60)
    stats = dict(received=0, dropped=0, written=0, pose_updates=0, pose_failures=0)
    closing = threading.Event()

    def on_image(msg):
        if closing.is_set():
            return
        stats['received'] += 1
        stamp = msg.header.stamp.sec + msg.header.stamp.nsec * 1e-9
        try:
            pending.put_nowait((stamp, msg.width, msg.height, msg.step, bytes(msg.data)))
        except queue.Full:
            stats['dropped'] += 1

    if not node.subscribe(Image, topic, on_image):
        raise SystemExit('image subscription failed')

    def follow():
        heading = None
        last = None
        while not closing.is_set():
            with lock:
                pose, stamp = state['pose'], state['stamp']
            if pose is None:
                time.sleep(0.05)
                continue
            (x, y, z), yaw = pose
            if heading is None:
                heading = yaw
            elif last is not None and stamp > last:
                k = 1 - math.exp(-(stamp - last) / args.heading_tau)
                heading = wrap(heading + k * wrap(yaw - heading))
            last = stamp
            cx = x - args.back * math.cos(heading)
            cy = y - args.back * math.sin(heading)
            cz = max(z + args.up, 1.5)
            look_yaw = math.atan2(y - cy, x - cx)
            look_pitch = math.atan2(cz - z, math.hypot(x - cx, y - cy))   # + = down
            w, qx, qy, qz = quat(0.0, look_pitch, look_yaw)
            req = Pose(name=NAME)
            req.position.x, req.position.y, req.position.z = cx, cy, cz
            req.orientation.w, req.orientation.x, req.orientation.y, req.orientation.z = w, qx, qy, qz
            ok, res = node.request(f'/world/{args.world}/set_pose', req, Pose, Boolean, 1000)
            stats['pose_updates' if ok and res.data else 'pose_failures'] += 1
            time.sleep(0.03)

    threading.Thread(target=follow, daemon=True).start()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    started, last_stamp = time.monotonic(), None
    try:
        with (out / 'frames.jsonl').open('x') as ledger:
            while not stop.is_set() and time.monotonic() - started < args.max_s:
                if args.stop_file and args.stop_file.exists():
                    break
                try:
                    stamp, w, h, step, data = pending.get(timeout=1)
                except queue.Empty:
                    continue
                if stamp == last_stamp:
                    continue
                last_stamp = stamp
                rgb = np.frombuffer(data, np.uint8).reshape(h, step)[:, :w * 3].reshape(h, w, 3)
                rel = f'frames/frame_{stats["written"]:06d}.jpg'
                if not cv2.imwrite(str(out / rel), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                                   [cv2.IMWRITE_JPEG_QUALITY, 88]):
                    raise RuntimeError('frame write failed')
                with lock:
                    truth = state['pose']
                ledger.write(json.dumps(dict(stamp=stamp, file=rel,
                                             aircraft=None if truth is None else
                                             [round(v, 3) for v in truth[0]])) + '\n')
                ledger.flush()
                stats['written'] += 1
                if stats['written'] == 1:
                    (out / 'ready.json').write_text(json.dumps(dict(stamp=stamp)))
                    print('chase camera ready', flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        closing.set()
        node.unsubscribe(topic)
        (out / 'capture_summary.json').write_text(json.dumps(stats, indent=2))
        print(json.dumps(stats), flush=True)


if __name__ == '__main__':
    main()
