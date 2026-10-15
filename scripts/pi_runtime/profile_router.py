#!/usr/bin/env python3
"""Native Pi UART owner, following an explicitly selected vehicle profile."""
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import time

def main():
    source = Path('/home/pi5/.aerothon/vehicle_connection.json')
    proc = None
    signature = None
    stopping = False
    def stop(*_):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        while not stopping:
            try:
                p = json.loads(source.read_text()) if source.exists() else {}
                serial = p.get('transport') == 'serial' and p.get('hardware_reviewed') is True
                device = p.get('device', os.environ.get('AEROTHON_FCU_DEVICE','/dev/ttyAMA0'))
                baud = int(p.get('baud',os.environ.get('AEROTHON_FCU_BAUD','115200')))
                valid = serial and device.startswith('/dev/') and '..' not in device and Path(device).exists() and stat.S_ISCHR(Path(device).stat().st_mode)
                wanted = (device, baud) if valid else None
            except (OSError, ValueError, TypeError):
                wanted = None
            if signature != wanted or (proc and proc.poll() is not None):
                if proc and proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=5)
                proc = None
                signature = wanted
                if wanted:
                    proc = subprocess.Popen(['/usr/bin/python3','/home/pi5/aerothon_ws/scripts/mav_router.py',
                        '--fcu-serial',wanted[0],'--fcu-baud',str(wanted[1]),'--mavros-port','14555','--gcs-port','14550'])
                    print(f'UART owner started: {wanted[0]} at {wanted[1]}', flush=True)
            time.sleep(.5)
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)

if __name__ == '__main__':
    main()
