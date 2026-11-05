"""Loopback-only SSH broker for the 15 October Pi deployment.

The operator types the Pi password once (getpass); it stays in this process.
Requests arrive as one JSON line per connection on 127.0.0.1 only:
  {"action": "exec"|"sudo", "command": "...", "timeout": s}
  {"action": "put"|"get", "local": path, "remote": path}
Output streams back, then a final JSON line {"exit_code": n}.
"""
import getpass
import json
from pathlib import Path
import shlex
import socket
import sys
import time

import paramiko

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.0.102"
PORT = 47123
# Pi host key recorded in .scratch/pi_remote_runtime_20261014/known_hosts.
EXPECTED_KEY = "AAAAC3NzaC1lZDI1NTE5AAAAIEh/O7bwqcP5Ttxtbw2RjMDvwPbyRrWMpZYlDnzES9"

root = Path(__file__).resolve().parent
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
log = root / "broker.log"
for attempt in range(3):
    password = getpass.getpass(f"pi5@{HOST} password: ")
    try:
        client.connect(HOST, username="pi5", password=password,
                       look_for_keys=False, allow_agent=False, timeout=30,
                       banner_timeout=30, auth_timeout=30)
        break
    except Exception as error:
        message = f"Login attempt {attempt + 1} failed: {error!r}"
        print(message, flush=True)
        log.open("a").write(time.strftime("%H:%M:%S ") + message + "\n")
else:
    input("Press Enter to close.")
    sys.exit(1)
log.open("a").write(time.strftime("%H:%M:%S ") + "connected\n")
key = client.get_transport().get_remote_server_key().get_base64()
if not key.startswith(EXPECTED_KEY):
    client.close()
    sys.exit(f"Host key mismatch: {key[:60]}")
client.get_transport().set_keepalive(15)
print(json.dumps({"connected": HOST, "host_key_verified": True}), flush=True)

server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("127.0.0.1", PORT))
server.listen(1)
print(f"Listening on 127.0.0.1:{PORT}. Ctrl-C to close.", flush=True)


def run(conn, request):
    action = request["action"]
    if action in ("put", "get"):
        with client.open_sftp() as sftp:
            if action == "put":
                sftp.put(request["local"], request["remote"])
            else:
                sftp.get(request["remote"], request["local"])
        conn.sendall((json.dumps({"exit_code": 0}) + "\n").encode())
        return
    command = request["command"]
    channel = client.get_transport().open_session()
    channel.settimeout(1)
    if action == "sudo":
        channel.exec_command("sudo -S -p '' bash -c " + shlex.quote(command))
        channel.sendall(password + "\n")
        channel.shutdown_write()
    else:
        channel.exec_command(command)
    start = time.monotonic()
    limit = request.get("timeout", 1800)
    while True:
        moved = False
        if channel.recv_ready():
            conn.sendall(channel.recv(65536)); moved = True
        if channel.recv_stderr_ready():
            conn.sendall(channel.recv_stderr(65536)); moved = True
        if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
            break
        if time.monotonic() - start > limit:
            channel.close()
            conn.sendall(b'\n{"exit_code": "timeout"}\n')
            return
        if not moved:
            time.sleep(0.05)
    conn.sendall(("\n" + json.dumps({"exit_code": channel.recv_exit_status()}) + "\n").encode())
    channel.close()


try:
    while True:
        conn, _ = server.accept()
        with conn:
            data = b""
            while not data.endswith(b"\n"):
                chunk = conn.recv(65536)
                if not chunk:
                    break
                data += chunk
            try:
                request = json.loads(data)
                print(time.strftime("%H:%M:%S"), request["action"],
                      str(request.get("command", request.get("remote", "")))[:100], flush=True)
                run(conn, request)
            except Exception as error:  # report and keep serving
                conn.sendall(("\n" + json.dumps({"error": repr(error)}) + "\n").encode())
finally:
    client.close()
