"""Harmless sleeper to exercise only the prepared detached launcher."""
import argparse
import os
import time

parser = argparse.ArgumentParser()
parser.add_argument('--seconds', type=float, required=True)
parser.add_argument('--exit-code', type=int, default=0)
args = parser.parse_args()
print(f'smoke process pid={os.getpid()} pgid={os.getpgid(0)}', flush=True)
time.sleep(args.seconds)
print(f'smoke process finished with exit {args.exit_code}', flush=True)
raise SystemExit(args.exit_code)
