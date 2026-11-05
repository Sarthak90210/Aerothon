#!/usr/bin/env python3
"""Detached Linux job with persistent status and PID-reuse-safe scoped stop.

Commands are passed as an argument array. No shell interpretation is added.
Use only for a task-owned command whose own cleanup handles escaped child groups.
"""
import argparse
import errno
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def atomic_json(path, value):
    temporary = path.with_name(path.name + '.writing')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def read_json(path):
    # DrvFS can expose a brief replacement gap even when a preceding exists()
    # saw the old file. Retry the read, never launch a second copy of the job.
    for attempt in range(25):
        try:
            return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            if isinstance(error, OSError) and not isinstance(error, FileNotFoundError) and error.errno != errno.ENODATA:
                raise
            if attempt == 24:
                raise
            time.sleep(.02)


def identity(pid):
    try:
        text = Path(f'/proc/{pid}/stat').read_text()
        fields = text[text.rindex(')') + 2:].split()
        return dict(pid=pid, pgid=os.getpgid(pid), start_ticks=int(fields[19]),
                    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
    except (FileNotFoundError, ProcessLookupError):
        return None


def same_process(record):
    return record is not None and identity(record['pid']) == record


def supervise(job):
    definition = read_json(job / 'job.json')
    status_path = job / 'status.json'
    supervisor = identity(os.getpid())
    child = None
    running = dict(state='STARTING', started_wall=time.time(), supervisor=supervisor,
                   command=definition['command'], cwd=definition['cwd'])
    atomic_json(status_path, running)
    try:
        with (job / 'output.log').open('ab', buffering=0) as output:
            child = subprocess.Popen(definition['command'], cwd=definition['cwd'],
                stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                start_new_session=True)
            running.update(state='RUNNING', command_process=identity(child.pid))
            atomic_json(status_path, running)
            code = child.wait()
        stopped = (job / 'stop_requested.json').exists()
        running.update(state='STOPPED' if stopped else 'COMPLETED' if code == 0 else 'FAILED',
                       exit_code=code, finished_wall=time.time())
        (job / 'exit_code.txt').write_text(str(code) + '\n')
        atomic_json(status_path, running)
        return 0
    except BaseException as error:
        running.update(state='SUPERVISOR_ERROR', error=repr(error), finished_wall=time.time())
        atomic_json(status_path, running)
        if child is not None and child.poll() is None:
            # The command owns this separate group. Its TERM trap handles cleanup.
            os.killpg(child.pid, signal.SIGTERM)
        return 1


def start(job, cwd, command):
    if command and command[0] == '--':
        command = command[1:]
    if not command:
        raise SystemExit('A command argument array is required after --')
    job = job.resolve()
    cwd = cwd.resolve(strict=True)
    if not cwd.is_dir():
        raise SystemExit('Working directory is not a directory')
    job.mkdir(parents=True, exist_ok=False)
    atomic_json(job / 'job.json', dict(command=command, cwd=str(cwd), created_wall=time.time()))
    with (job / 'supervisor.log').open('ab', buffering=0) as output:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
            '_supervise', '--job', str(job)], cwd=cwd, stdin=subprocess.DEVNULL,
            stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
    # Return after startup, so the tool client never owns the long-running wait.
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        path = job / 'status.json'
        if path.exists():
            status = read_json(path)
            if status['state'] != 'STARTING':
                print(json.dumps(dict(job=str(job), **status), indent=2))
                return 0 if status['state'] in ('RUNNING', 'COMPLETED') else 1
        if process.poll() is not None:
            raise SystemExit('Supervisor exited before readiness; inspect supervisor.log')
        time.sleep(.05)
    raise SystemExit('Supervisor readiness timed out; inspect task-owned job status before retrying')


def status(job):
    value = read_json(job / 'status.json')
    value['supervisor_alive'] = same_process(value.get('supervisor'))
    value['command_alive'] = same_process(value.get('command_process'))
    print(json.dumps(value, indent=2))
    return 0


def stop(job, grace):
    value = read_json(job / 'status.json')
    if value['state'] != 'RUNNING':
        print(json.dumps(value, indent=2))
        return 0
    command = value.get('command_process')
    if not same_process(command) or command['pgid'] != command['pid']:
        raise SystemExit('Recorded command identity no longer matches; no signal was sent')
    atomic_json(job / 'stop_requested.json', dict(requested_wall=time.time(),
        command_process=command, grace_seconds=grace))
    os.killpg(command['pgid'], signal.SIGTERM)
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        value = read_json(job / 'status.json')
        if value['state'] != 'RUNNING':
            print(json.dumps(value, indent=2))
            return 0
        time.sleep(.1)
    if same_process(command):
        os.killpg(command['pgid'], signal.SIGKILL)
    # A healthy supervisor writes the authoritative exit code after reap.
    print('TERM grace elapsed; KILL was limited to the verified command group. Inspect status.json.')
    return 0


def main():
    if os.name != 'posix' or not Path('/proc/sys/kernel/random/boot_id').exists():
        raise SystemExit('Use this helper inside Linux/WSL')
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    launch = actions.add_parser('start')
    launch.add_argument('--job', type=Path, required=True)
    launch.add_argument('--cwd', type=Path, required=True)
    launch.add_argument('command', nargs=argparse.REMAINDER)
    for name in ('status', '_supervise', 'stop'):
        subparser = actions.add_parser(name)
        subparser.add_argument('--job', type=Path, required=True)
        if name == 'stop':
            subparser.add_argument('--grace', type=float, default=30.)
    args = parser.parse_args()
    if args.action == 'start':
        return start(args.job, args.cwd, args.command)
    job = args.job.resolve(strict=True)
    if args.action == 'status':
        return status(job)
    if args.action == 'stop':
        if not 0 < args.grace <= 60:
            raise SystemExit('Grace must be positive and at most 60 seconds')
        return stop(job, args.grace)
    return supervise(job)


if __name__ == '__main__':
    raise SystemExit(main())
