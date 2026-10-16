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
    started, delay, retry_at = 0.0, 0.5, 0.0
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
                gcs_host = str(p.get('gcs_host') or '').strip()
                if gcs_host and not all(c.isalnum() or c in '.:-' for c in gcs_host):
                    gcs_host = ''
                # Every Mission Planner on the LAN gets the FC's MAVLink by
                # default (UDP listen on 14550, no laptop IP to configure).
                broadcast = p.get('gcs_broadcast', True) is not False
                wanted = (device, baud, gcs_host, broadcast) if valid else None
            except (OSError, ValueError, TypeError):
                wanted = None
            died = proc is not None and proc.poll() is not None
            if died and signature == wanted:
                # A router that dies at once (port held by a getty, pyserial
                # missing) was relaunched every 0.5 s: a flapping UART and two
                # journal lines a second. Back off, up to 30 s, and say why.
                quick = time.monotonic() - started < 5.0
                delay = min(30.0, delay * 2) if quick else 0.5
                if quick:
                    print(f'UART owner exited (code {proc.returncode}) {time.monotonic() - started:.1f} s '
                          f'after start; retrying in {delay:.0f} s', flush=True)
                proc = None
                retry_at = time.monotonic() + delay
            if signature != wanted or (proc is None and wanted and time.monotonic() >= retry_at):
                if proc and proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=5)
                if signature != wanted:
                    delay, retry_at = 0.5, 0.0
                proc = None
                signature = wanted
                if wanted:
                    started = time.monotonic()
                    # MAVROS on the Pi and a GCS port (14550) for the laptop;
                    # with gcs_host the FC's MAVLink is also pushed to it.
                    cmd = ['/usr/bin/python3','/home/pi5/aerothon_ws/scripts/mav_router.py',
                        '--fcu-serial',wanted[0],'--fcu-baud',str(wanted[1]),'--mavros-port','14555','--gcs-port','14550']
                    if wanted[2]:
                        cmd += ['--gcs-host', wanted[2], '--gcs-out-port', '14550']
                    if wanted[3]:
                        cmd += ['--gcs-broadcast']
                    proc = subprocess.Popen(cmd)
                    print(f'UART owner started: {wanted[0]} at {wanted[1]}'
                          + (f', MAVLink to {wanted[2]}:14550' if wanted[2] else '')
                          + (', LAN broadcast :14550' if wanted[3] else ''), flush=True)
            time.sleep(.5)
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)

if __name__ == '__main__':
    main()
