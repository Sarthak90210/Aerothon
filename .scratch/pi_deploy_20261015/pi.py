"""Client for broker.py: pi.py exec|sudo CMD [timeout] | pi.py put|get LOCAL REMOTE."""
import json
import socket
import sys

action = sys.argv[1]
if action in ("put", "get"):
    request = {"action": action, "local": sys.argv[2], "remote": sys.argv[3]}
else:
    request = {"action": action, "command": sys.argv[2],
               "timeout": int(sys.argv[3]) if len(sys.argv) > 3 else 1800}
with socket.create_connection(("127.0.0.1", 47123)) as conn:
    conn.sendall((json.dumps(request) + "\n").encode())
    tail = b""
    while True:
        chunk = conn.recv(65536)
        if not chunk:
            break
        sys.stdout.buffer.write(chunk)
        sys.stdout.flush()
        tail = (tail + chunk)[-200:]
last = tail.decode(errors="replace").strip().splitlines()[-1] if tail.strip() else "{}"
try:
    sys.exit(0 if json.loads(last).get("exit_code") == 0 else 1)
except ValueError:
    sys.exit(1)
