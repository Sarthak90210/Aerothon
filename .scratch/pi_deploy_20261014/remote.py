"""Temporary SSH/SFTP session for the authorised Pi deployment."""
import getpass
import hashlib
import json
from pathlib import Path
import shlex
import sys
import time

import paramiko


class ReportHostKey(paramiko.MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        import base64
        digest = base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")
        print(json.dumps({"host": hostname, "host_key": key.get_name(), "sha256": digest}), flush=True)
        client._host_keys.add(hostname, key.get_name(), key)


local_root = Path(__file__).resolve().parent
client = paramiko.SSHClient()
client.load_system_host_keys()
known_hosts = local_root / "known_hosts"
if known_hosts.exists():
    client.load_host_keys(str(known_hosts))
client.set_missing_host_key_policy(ReportHostKey())
ssh_password = getpass.getpass("Pi SSH password: ")
client.connect("192.168.0.101", username="pi5", password=ssh_password,
               look_for_keys=False, allow_agent=False, timeout=15)
client.save_host_keys(str(known_hosts))
print(json.dumps({"connected": True}), flush=True)

try:
    for line in sys.stdin:
        request = json.loads(line)
        try:
            action = request["action"]
            if action == "quit":
                break
            if action in ("exec", "sudo"):
                command = request.get("command")
                if command is None:
                    command = Path(request["script"]).read_text(encoding="utf-8")
                channel = client.get_transport().open_session()
                channel.settimeout(1)
                if action == "sudo":
                    channel.exec_command("sudo -S -p '' bash -c " + shlex.quote(command))
                    channel.sendall(ssh_password + "\n")
                    channel.shutdown_write()
                else:
                    channel.exec_command(command)
                limit = request.get("timeout", 1800)
                start = time.monotonic()
                log_path = local_root / (request.get("log", "remote_transcript.log"))
                log_file = log_path.open("a", encoding="utf-8")
                while True:
                    if channel.recv_ready():
                        chunk = channel.recv(65536).decode(errors="replace")
                        log_file.write(chunk)
                        log_file.flush()
                        print(chunk, end="", flush=True)
                    if channel.recv_stderr_ready():
                        chunk = channel.recv_stderr(65536).decode(errors="replace")
                        log_file.write(chunk)
                        log_file.flush()
                        print(chunk, end="", flush=True)
                    if channel.exit_status_ready() and not channel.recv_ready() and not channel.recv_stderr_ready():
                        break
                    if time.monotonic() - start > limit:
                        channel.close()
                        log_file.close()
                        raise TimeoutError("Remote command exceeded its time limit")
                    time.sleep(0.05)
                print(json.dumps({"exit_code": channel.recv_exit_status()}), flush=True)
                log_file.close()
                channel.close()
            elif action in ("put", "get"):
                with client.open_sftp() as sftp:
                    if action == "put":
                        sftp.put(request["local"], request["remote"])
                        if "mode" in request:
                            sftp.chmod(request["remote"], request["mode"])
                    else:
                        sftp.get(request["remote"], request["local"])
                print(json.dumps({"transferred": request["remote"]}), flush=True)
            else:
                raise ValueError("Unknown action")
        except Exception as error:
            print(json.dumps({"error": str(error), "type": type(error).__name__}), flush=True)
finally:
    client.close()
