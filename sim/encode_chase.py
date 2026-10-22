#!/usr/bin/env python3
"""Encode a sim/record_chase.py capture to MP4 with the mission stage overlaid.

    python3 sim/encode_chase.py RUN_DIR [--speed 2] [--out RUN_DIR/chase.mp4]

Frames play at capture_hz x speed. The overlay is the simulated time since
the first frame and the mission state from RUN_DIR/states.jsonl (t_sim), when
present. Evaluation only.
"""
import argparse
import bisect
import json
from pathlib import Path
import subprocess

import cv2


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('run', type=Path)
    ap.add_argument('--speed', type=float, default=2.0)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--crf', type=int, default=26)
    ap.add_argument('--from-state', default='',
                    help='start 3 s before the LAST time the mission entered this '
                         'state (e.g. ARMING), skipping an idle wait before Start')
    args = ap.parse_args()
    chase = args.run / 'chase'
    cfg = json.loads((chase / 'configuration.json').read_text())
    frames = [json.loads(line) for line in (chase / 'frames.jsonl').read_text().splitlines() if line]
    if not frames:
        raise SystemExit('no frames')
    states = []
    if (args.run / 'states.jsonl').exists():
        states = [json.loads(line) for line in (args.run / 'states.jsonl').read_text().splitlines() if line]
    st_t = [s['t_sim'] for s in states]
    if args.from_state:
        starts = [s['t_sim'] for s in states if s['state'] == args.from_state]
        if starts:
            frames = [f for f in frames if f['stamp'] >= starts[-1] - 3.0] or frames
    out = args.out or (args.run / 'chase.mp4')
    first = cv2.imread(str(chase / frames[0]['file']))
    h, w = first.shape[:2]
    fps = cfg['capture_hz'] * args.speed
    ff = subprocess.Popen(
        ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
         '-s', f'{w}x{h}', '-r', f'{fps:g}', '-i', '-', '-c:v', 'libx264',
         '-preset', 'medium', '-crf', str(args.crf), '-pix_fmt', 'yuv420p',
         '-movflags', '+faststart', str(out)], stdin=subprocess.PIPE)
    t0 = frames[0]['stamp']
    for f in frames:
        img = cv2.imread(str(chase / f['file']))
        if img is None:
            continue
        i = bisect.bisect_right(st_t, f['stamp']) - 1
        stage = states[i]['state'] if i >= 0 else ''
        text = f"t+{f['stamp'] - t0:6.1f} s sim   {stage}"
        tag = f"{args.speed:g}x"
        for colour, thick in (((0, 0, 0), 5), ((255, 255, 255), 2)):
            cv2.putText(img, text, (24, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.0, colour, thick, cv2.LINE_AA)
            cv2.putText(img, tag, (w - 90, 48), cv2.FONT_HERSHEY_SIMPLEX, 1.0, colour, thick, cv2.LINE_AA)
        ff.stdin.write(img.tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit('ffmpeg failed')
    print(json.dumps(dict(out=str(out), frames=len(frames), fps=fps,
                          sim_s=round(frames[-1]['stamp'] - t0, 1))))


if __name__ == '__main__':
    main()
