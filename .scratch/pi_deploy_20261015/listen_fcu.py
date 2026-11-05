"""Read-only: listen on the FC UART and count MAVLink frames; sends nothing."""
import os, sys, termios, time
dev, baud = sys.argv[1], int(sys.argv[2])
rates = {57600: termios.B57600, 115200: termios.B115200, 230400: termios.B230400, 460800: termios.B460800, 921600: termios.B921600}
fd = os.open(dev, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
a = termios.tcgetattr(fd)
a[0] = 0; a[1] = 0; a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL; a[3] = 0
a[4] = a[5] = rates[baud]
termios.tcsetattr(fd, termios.TCSANOW, a)
buf = b""; t0 = time.time()
while time.time() - t0 < 4:
    try: buf += os.read(fd, 4096)
    except BlockingIOError: time.sleep(0.02)
os.close(fd)
v2 = buf.count(b"\xfd"); v1 = buf.count(b"\xfe")
hb = 0; sysids = set()
i = 0
while i < len(buf) - 10:
    if buf[i] == 0xFD and i + 10 <= len(buf):
        msgid = buf[i+7] | (buf[i+8] << 8) | (buf[i+9] << 16)
        if msgid == 0: hb += 1; sysids.add((buf[i+5], buf[i+6]))
    i += 1
print({"device": dev, "baud": baud, "bytes": len(buf), "v2_magic": v2, "v1_magic": v1, "heartbeats_v2": hb, "sys_comp": sorted(sysids)})
