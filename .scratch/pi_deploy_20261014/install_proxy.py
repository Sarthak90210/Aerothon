"""Temporary loopback-only installation proxy over the authorised SSH link."""
import getpass
from pathlib import Path
import select
import socket
import socketserver
import threading
import time
from urllib.parse import urlsplit

import paramiko


def relay(left, right):
    try:
        while True:
            ready, _, _ = select.select([left, right], [], [], 300)
            if not ready:
                break
            for source in ready:
                data = source.recv(65536)
                if not data:
                    return
                (right if source is left else left).sendall(data)
    finally:
        left.close()
        right.close()


class Proxy(socketserver.BaseRequestHandler):
    def handle(self):
        upstream = None
        try:
            raw = b""
            self.request.settimeout(20)
            while b"\r\n\r\n" not in raw:
                block = self.request.recv(65536)
                if not block or len(raw) > 65536:
                    return
                raw += block
            headers, tail = raw.split(b"\r\n\r\n", 1)
            rows = headers.decode("iso-8859-1").split("\r\n")
            method, target, protocol = rows[0].split(" ", 2)
            if method == "CONNECT":
                hostname, port = target.rsplit(":", 1)
                upstream = socket.create_connection((hostname, int(port)), timeout=20)
                self.request.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                if tail:
                    upstream.sendall(tail)
            else:
                url = urlsplit(target)
                if url.scheme != "http" or not url.hostname:
                    raise ValueError("Only absolute HTTP URLs are supported")
                upstream = socket.create_connection((url.hostname, url.port or 80), timeout=20)
                path = (url.path or "/") + (("?" + url.query) if url.query else "")
                rows[0] = f"{method} {path} {protocol}"
                rows = [row for row in rows if not row.lower().startswith(("connection:", "proxy-connection:"))]
                rows.append("Connection: close")
                upstream.sendall(("\r\n".join(rows) + "\r\n\r\n").encode("iso-8859-1") + tail)
            self.request.settimeout(None)
            upstream.settimeout(None)
            relay(self.request, upstream)
        except Exception as error:
            print(f"Proxy request failed: {type(error).__name__}: {error}", flush=True)
            try:
                self.request.sendall(b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
            except OSError:
                pass
            if upstream:
                upstream.close()


server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Proxy)
server.daemon_threads = True
threading.Thread(target=server.serve_forever, daemon=True).start()
client = paramiko.SSHClient()
client.load_host_keys(str(Path(__file__).with_name("known_hosts")))
password = getpass.getpass("Pi SSH password: ")
client.connect("192.168.0.101", username="pi5", password=password,
               look_for_keys=False, allow_agent=False, timeout=15)
del password


def forward(channel, origin, destination):
    connection = socket.create_connection(server.server_address, timeout=10)
    threading.Thread(target=relay, args=(channel, connection), daemon=True).start()


client.get_transport().request_port_forward("127.0.0.1", 3128, handler=forward)
print("Temporary Pi installation proxy ready at 127.0.0.1:3128 over SSH.", flush=True)
try:
    while client.get_transport().is_active():
        time.sleep(1)
finally:
    client.close()
    server.shutdown()
