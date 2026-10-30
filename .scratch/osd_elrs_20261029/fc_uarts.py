"""Read-only: @SYS/uarts.txt over MAVLink FTP (the FC's per-port byte rates),
twice, 3 s apart. ArduPilot generates it on each read."""
import struct
import sys
import time
from pymavlink import mavutil

m = mavutil.mavlink_connection("udpout:127.0.0.1:14550", source_system=250,
                               source_component=191, dialect="ardupilotmega")
m.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
m.recv_match(type="HEARTBEAT", blocking=True, timeout=5)
seq = 0


def ftp(opcode, session=0, offset=0, data=b"", size=None):
    global seq
    seq = (seq + 1) & 0xFFFF
    size = len(data) if size is None else size
    payload = struct.pack("<HBBBBBBI", seq, session, opcode, size, 0, 0, 0, offset) + data
    payload = payload.ljust(251, b"\0")
    for _ in range(5):
        m.mav.file_transfer_protocol_send(0, 1, 1, list(payload))
        end = time.time() + 1.5
        while time.time() < end:
            r = m.recv_match(type="FILE_TRANSFER_PROTOCOL", blocking=True, timeout=0.5)
            if not r:
                continue
            p = bytes(r.payload)
            rseq, rsess, rop, rsize, rreq, _, _, roff = struct.unpack("<HBBBBBBI", p[:12])
            if rreq == opcode and rseq == (seq + 1) & 0xFFFF:   # the reply increments it
                seq = rseq
                return rop, rsess, p[12:12 + rsize]
    sys.exit(f"no FTP reply to opcode {opcode}")


def read(path):
    ftp(2)                                        # reset sessions
    op, sess, data = ftp(4, data=path.encode())   # open read-only
    if op != 128:
        sys.exit(f"open {path} refused: {list(data)}")
    out, offset = b"", 0
    while True:
        op, _, data = ftp(5, session=sess, offset=offset, size=239)
        if op != 128 or not data:
            break
        out += data
        offset += len(data)
    ftp(1, session=sess)                          # terminate
    return out.decode(errors="replace")


read("@SYS/uarts.txt")
time.sleep(3)
print(read("@SYS/uarts.txt"))
