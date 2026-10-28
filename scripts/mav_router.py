#!/usr/bin/env python3
"""High-performance bi-directional MAVLink UDP router.

Routes MAVLink telemetry between:
  1) ArduPilot SITL / Serial FCU (default: listen on UDP 127.0.0.1:14550 or connect to SITL 5760/14550)
  2) Local MAVROS (UDP 127.0.0.1:14555)
  3) External GCS / Mission Planner / QGroundControl (UDP 0.0.0.0:14550 or 14551)
  4) Companion Computer / GCS Aggregator (UDP 127.0.0.1:14552)

Usage:
  python3 scripts/mav_router.py --fcu-in 14560 --mavros-out 14555 --gcs-out 14550
"""
import argparse
import ipaddress
import logging
import select
import socket
import subprocess
import time
from pathlib import Path

import serial

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (MAVRouter) %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("mav_router")

# Container bridges and virtual links are not the operator network.
VIRTUAL_PREFIXES = ("lo", "docker", "br-", "veth", "virbr")


class GcsTelemetryBatch:
    """Coalesce UART fragments for the LAN, bounded by 10 ms and 1200 bytes.

    Serial readiness can fire for a single byte. Broadcasting each read flooded
    Wi-Fi with thousands of packets/s. MAVROS and inbound commands stay immediate.
    """
    def __init__(self):
        self.pending = bytearray()
        self.deadline = None

    def append(self, data, now):
        if not self.pending:
            self.deadline = now + .01
        self.pending.extend(data)

    def ready(self, now):
        if not self.pending or (len(self.pending) < 1200 and now < self.deadline):
            return []
        packets = [bytes(self.pending[i:i+1200]) for i in range(0, len(self.pending), 1200)]
        self.pending.clear()
        self.deadline = None
        return packets


def lan_interfaces(ip_output):
    """[(interface_ip, network, broadcast)] from `ip -o -4 addr show` text."""
    found = []
    for line in ip_output.splitlines():
        parts = line.split()
        if len(parts) < 4 or parts[2] != "inet" or "brd" not in parts:
            continue
        if parts[1].startswith(VIRTUAL_PREFIXES):
            continue
        iface = ipaddress.ip_interface(parts[3])
        found.append((str(iface.ip), iface.network, parts[parts.index("brd") + 1]))
    return found


def read_ip_addr():
    try:
        return subprocess.run(["ip", "-o", "-4", "addr", "show"], capture_output=True,
                              text=True, timeout=2).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def read_lan_interfaces():
    return lan_interfaces(read_ip_addr())


# ---------------------------------------------------------------------------
# The Pi tells the operator it is up (operator, 29 Oct 2026). One MAVLink 2
# STATUSTEXT from the FC's system as its onboard computer: Mission Planner
# copies another component's text into the vehicle's Messages tab as
# "191 : ...". Sent to the FC, which forwards a broadcast to its other ports
# (USB), and to the Wi-Fi GCS endpoints, which the FC does not echo back to.
# ---------------------------------------------------------------------------
STATUSTEXT_ID, STATUSTEXT_CRC_EXTRA = 253, 83
MAV_COMP_ID_ONBOARD_COMPUTER, MAV_SEVERITY_INFO = 191, 6


def x25_crc(data, crc=0xFFFF):
    """MAVLink's CRC-16/MCRF4XX."""
    for b in data:
        tmp = (b ^ crc) & 0xFF
        tmp = (tmp ^ (tmp << 4)) & 0xFF
        crc = ((crc >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4)) & 0xFFFF
    return crc


def statustext_frame(text, seq, sysid=1, compid=MAV_COMP_ID_ONBOARD_COMPUTER,
                     severity=MAV_SEVERITY_INFO):
    """A MAVLink 2 STATUSTEXT: ASCII, at most 50 characters."""
    body = text.encode("ascii", "replace")[:50]
    payload = (bytes([severity]) + body).rstrip(b"\0") or b"\0"   # v2 trims trailing zeros
    header = bytes([0xFD, len(payload), 0, 0, seq & 0xFF, sysid, compid,
                    STATUSTEXT_ID & 0xFF, 0, 0])
    crc = x25_crc(header[1:] + payload)
    crc = x25_crc(bytes([STATUSTEXT_CRC_EXTRA]), crc)
    return header + payload + crc.to_bytes(2, "little")


def wifi_interfaces(ip_output):
    """[(interface, ip)] for the Wi-Fi interfaces in `ip -o -4 addr show` text."""
    found = []
    for line in ip_output.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[2] == "inet" and parts[1].startswith("wl"):
            found.append((parts[1], parts[3].split("/")[0]))
    return found


def read_ssid(interface):
    """The network a Wi-Fi interface joined, or "" when no tool says."""
    for cmd in (["iwgetid", "-r", interface],
                ["nmcli", "-t", "-g", "GENERAL.CONNECTION", "device", "show", interface]):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=2).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            continue
        if out:
            return out.splitlines()[0]
    return ""


def read_uptime():
    try:
        return float(Path("/proc/uptime").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return None


class PiAnnouncer:
    """'Pi booted' once the FC link carries data, then 'Pi Wi-Fi up' for each
    Wi-Fi address that appears. A GCS that connects over Wi-Fi later is sent
    the latest of each, so it does not miss them."""

    def __init__(self, sysid=1, uptime=read_uptime, ssid=read_ssid):
        self.sysid, self.uptime, self.ssid = sysid, uptime, ssid
        self.seq = 0
        self.fcu_seen = False
        self.wifi = set()
        self.latest = {}             # kind -> text, resent to a new GCS

    def _frame(self, text):
        self.seq += 1
        return statustext_frame(text, self.seq, sysid=self.sysid)

    def _say(self, kind, text):
        self.latest[kind] = text
        logger.info(f"Announced to the FC: {text}")
        return [self._frame(text)]

    def on_fcu_data(self, wifi):
        """Frames to send on the first data from the FC (else none)."""
        if self.fcu_seen:
            return []
        self.fcu_seen = True
        up = self.uptime()
        frames = self._say("boot", "Pi booted" + (f" {up:.0f} s ago" if up is not None else ""))
        return frames + self.on_wifi(wifi)

    def on_wifi(self, wifi):
        """Frames for Wi-Fi addresses new since the last call (once the FC is seen)."""
        if not self.fcu_seen:
            return []
        frames = []
        for interface, ip in wifi:
            if (interface, ip) not in self.wifi:
                ssid = self.ssid(interface)
                frames += self._say("wifi", f"Pi Wi-Fi up: {ssid + ' ' if ssid else ''}{ip}")
        self.wifi = set(wifi)
        return frames

    def for_new_gcs(self):
        return [self._frame(t) for t in self.latest.values()]


def gcs_destinations(learned, configured, lans, out_port, broadcast):
    """Where one FCU datagram goes: every learned and configured GCS, plus the
    LAN broadcast so any Mission Planner listening on UDP out_port receives it
    with no IP configured. A learned sender already reached by that broadcast
    (same port, same subnet) is skipped, or it would get every packet twice."""
    dests = set(configured)
    if broadcast:
        dests |= {(b, out_port) for _, _, b in lans}
    for host, port in learned:
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            dests.add((host, port))
            continue
        if broadcast and port == out_port and any(ip in net for _, net, _ in lans):
            continue
        dests.add((host, port))
    return dests


def own_echo(addr, lans, out_port):
    """True for our own LAN broadcast arriving back on the GCS socket."""
    return addr[1] == out_port and any(addr[0] == ip for ip, _, _ in lans)


def run_router(fcu_port=14560, mavros_port=14555, gcs_port=14550,
               gcs_host=None, gcs_out_port=None, extra_ports=None,
               fcu_serial=None, fcu_baud=921600, gcs_broadcast=False,
               announce=None, announce_sysid=1):
    if extra_ports is None:
        extra_ports = [14551, 14552]
    # The aircraft (a serial FC) announces the Pi; the simulator does not.
    announcer = PiAnnouncer(sysid=announce_sysid) if (fcu_serial if announce is None else announce) else None
    wifi = wifi_interfaces(read_ip_addr()) if announcer else []
    t_last_wifi = time.time()

    # Use UDP for SITL, or open the Pixhawk telemetry device directly on the Pi.
    if fcu_serial:
        # Reads stay non-blocking; WRITES block briefly. With write_timeout=0
        # a full UART buffer (115200 baud carrying Mission Planner and MAVROS)
        # raised on write and the rest of the packet was silently dropped:
        # MAVROS's requests never reached the FC (16 October, real drone).
        fcu_link = serial.Serial(
            fcu_serial, baudrate=fcu_baud, timeout=0, write_timeout=0.5)
        fcu_sock = None
    else:
        fcu_link = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        fcu_link.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        fcu_link.bind(("0.0.0.0", fcu_port))
        fcu_link.setblocking(False)
        fcu_sock = fcu_link

    # Socket listening for GCS / Mission Planner connections
    gcs_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    gcs_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    gcs_sock.bind(("0.0.0.0", gcs_port))
    gcs_sock.setblocking(False)
    out_port = gcs_out_port or gcs_port
    lans = read_lan_interfaces() if gcs_broadcast else []
    if gcs_broadcast:
        gcs_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    t_last_lan = time.time()

    # Socket for MAVROS communication
    mavros_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    mavros_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Separate router command ingress from MAVROS telemetry ingress. Binding
    # both processes to 14555 with SO_REUSEADDR silently drops packets.
    mavros_sock.bind(("127.0.0.1", mavros_port + 1))
    mavros_sock.setblocking(False)

    # Registered client endpoints (IP, port)
    clients = {"mavros": ("127.0.0.1", mavros_port)}
    configured_gcs = set()
    if gcs_host:
        configured_gcs.add((gcs_host, gcs_out_port or gcs_port))
    
    # Active endpoints that have sent packets to us
    active_gcs_senders = {}
    active_fcu_senders = set()
    active_mavros_senders = set()

    logger.info("=========================================================")
    logger.info(" MAVLink High-Speed UDP Router Active")
    logger.info("=========================================================")
    if fcu_serial:
        logger.info(f"  FCU Link              : serial {fcu_serial} @ {fcu_baud}")
    else:
        logger.info(f"  FCU Ingress Port      : UDP 0.0.0.0:{fcu_port}")
    logger.info(f"  MAVROS Port           : UDP 127.0.0.1:{mavros_port}")
    logger.info(f"  Mission Planner / GCS : UDP 0.0.0.0:{gcs_port}")
    for host, port in configured_gcs:
        logger.info(f"  Mission Planner output: UDP {host}:{port}")
    if gcs_broadcast:
        logger.info(f"  LAN broadcast output  : UDP {', '.join(b for _, _, b in lans) or 'no LAN yet'}:{out_port}")
    logger.info("=========================================================")

    dropped = [0]

    def write_fcu(data):
        # Whole datagram or nothing: a partial MAVLink frame corrupts the next.
        try:
            fcu_link.write(data)
            fcu_link.flush()
        except serial.SerialTimeoutException:
            dropped[0] += 1

    def announce_frames(frames, gcs=None):
        """To the FC (forwarded to USB) and to the Wi-Fi GCS, or to one GCS."""
        for frame in frames:
            if gcs is None and fcu_serial:
                write_fcu(frame)
            for g_addr in ([gcs] if gcs else gcs_destinations(
                    active_gcs_senders, configured_gcs, lans, out_port, gcs_broadcast)):
                try:
                    gcs_sock.sendto(frame, g_addr)
                except OSError:
                    pass

    sockets = [fcu_link, gcs_sock, mavros_sock]
    packet_count = 0
    gcs_packet_count = 0
    gcs_batch = GcsTelemetryBatch()
    t_last_stat = time.time()

    try:
        while True:
            readable, _, _ = select.select(sockets, [], [], 0.01)

            for s in readable:
                try:
                    if fcu_serial and s is fcu_link:
                        data = fcu_link.read(4096)
                        addr = ("serial", fcu_serial)
                    else:
                        data, addr = s.recvfrom(4096)
                except Exception:
                    continue

                if not data:
                    continue

                packet_count += 1

                # 1. Packet from FCU (ArduPilot SITL / Pixhawk) -> Route to MAVROS + All connected GCS
                if s is fcu_link:
                    active_fcu_senders.add(addr)
                    # Forward to MAVROS
                    try:
                        mavros_sock.sendto(data, clients["mavros"])
                    except Exception:
                        pass
                    gcs_batch.append(data, time.monotonic())
                    if announcer:
                        announce_frames(announcer.on_fcu_data(wifi))

                # 2. Packet from GCS (Mission Planner / QGC commands) -> Route to FCU
                elif s is gcs_sock:
                    # Our own broadcast comes back to this socket. Fed to the
                    # FCU it would echo the FC's telemetry back into its UART.
                    if own_echo(addr, lans, out_port):
                        continue
                    if announcer and addr not in active_gcs_senders:
                        announce_frames(announcer.for_new_gcs(), gcs=addr)
                    active_gcs_senders[addr] = time.monotonic()
                    try:
                        if fcu_serial:
                            write_fcu(data)
                        else:
                            for f_addr in active_fcu_senders:
                                fcu_sock.sendto(data, f_addr)
                    except Exception:
                        pass

                # 3. Packet from MAVROS -> Route to FCU
                elif s is mavros_sock:
                    active_mavros_senders.add(addr)
                    try:
                        if fcu_serial:
                            write_fcu(data)
                        else:
                            for f_addr in active_fcu_senders:
                                fcu_sock.sendto(data, f_addr)
                    except Exception:
                        pass

            now = time.monotonic()
            for endpoint, seen in list(active_gcs_senders.items()):
                if now - seen > 30.:
                    del active_gcs_senders[endpoint]
            for packet in gcs_batch.ready(now):
                for g_addr in gcs_destinations(active_gcs_senders, configured_gcs,
                                               lans, out_port, gcs_broadcast):
                    try:
                        gcs_sock.sendto(packet, g_addr)
                        gcs_packet_count += 1
                    except OSError:
                        pass

            # DHCP can renumber the Pi; follow the LAN it is actually on.
            if gcs_broadcast and time.time() - t_last_lan > 1.0:
                fresh = read_lan_interfaces()
                if fresh != lans:
                    logger.info(f"LAN broadcast now {', '.join(b for _, _, b in fresh) or 'none'}:{out_port}")
                    lans = fresh
                t_last_lan = time.time()

            if announcer and time.time() - t_last_wifi > 2.0:
                wifi = wifi_interfaces(read_ip_addr())
                announce_frames(announcer.on_wifi(wifi))
                t_last_wifi = time.time()

            if time.time() - t_last_stat > 10.0:
                logger.info(f"Router status: {packet_count} pkts routed | "
                            f"{gcs_packet_count} GCS datagrams | "
                            f"{len(active_fcu_senders)} FCU, "
                            f"{len(active_mavros_senders)} MAVROS, "
                            f"{len(active_gcs_senders)} GCS endpoints active, "
                            f"{dropped[0]} FC writes timed out.")
                t_last_stat = time.time()

    except KeyboardInterrupt:
        logger.info("MAVRouter stopped by user.")
    finally:
        fcu_link.close()
        gcs_sock.close()
        mavros_sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MAVLink Multi-Endpoint Router")
    parser.add_argument("--fcu-in", type=int, default=14560, help="Port to receive MAVLink from SITL/FCU")
    parser.add_argument("--fcu-serial", help="Pixhawk serial device (for example /dev/ttyAMA0 or /dev/ttyACM0)")
    parser.add_argument("--fcu-baud", type=int, default=921600, help="Pixhawk serial baud rate")
    parser.add_argument("--mavros-port", type=int, default=14555, help="Port for MAVROS connection")
    parser.add_argument("--gcs-port", type=int, default=14550, help="Port for Mission Planner / QGC")
    parser.add_argument("--gcs-host", help="Laptop IP receiving Mission Planner MAVLink")
    parser.add_argument("--gcs-out-port", type=int, help="Laptop UDP listen port (default: --gcs-port)")
    parser.add_argument("--gcs-broadcast", action="store_true",
                        help="Also broadcast FCU MAVLink to every LAN on --gcs-out-port, "
                             "so any Mission Planner in UDP mode receives it")
    parser.add_argument("--no-announce", action="store_true",
                        help="Do not send 'Pi booted' / 'Pi Wi-Fi up' STATUSTEXT (on by default "
                             "with --fcu-serial)")
    parser.add_argument("--announce-sysid", type=int, default=1,
                        help="The FC's system id, sent as the onboard computer of it")
    args = parser.parse_args()

    run_router(fcu_port=args.fcu_in, mavros_port=args.mavros_port,
               gcs_port=args.gcs_port, gcs_host=args.gcs_host,
               gcs_out_port=args.gcs_out_port, fcu_serial=args.fcu_serial,
               fcu_baud=args.fcu_baud, gcs_broadcast=args.gcs_broadcast,
               announce=False if args.no_announce else None,
               announce_sysid=args.announce_sysid)
