"""Read-only: count LD06/LD19 packets (0x54 0x2C, 47 bytes) on a serial port."""
import os, sys, termios, time, struct
dev = sys.argv[1]
fd = os.open(dev, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
a = termios.tcgetattr(fd); a[0] = 0; a[1] = 0; a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL; a[3] = 0
a[4] = a[5] = termios.B230400; termios.tcsetattr(fd, termios.TCSANOW, a)
buf = b""; t0 = time.time()
while time.time() - t0 < 3:
    try: buf += os.read(fd, 8192)
    except BlockingIOError: time.sleep(0.01)
os.close(fd)
pk = [i for i in range(len(buf) - 47) if buf[i] == 0x54 and buf[i+1] == 0x2C]
speeds = [struct.unpack_from("<H", buf, i+2)[0] for i in pk[:50]]
dists = [struct.unpack_from("<H", buf, i+6+3*k)[0] for i in pk[:50] for k in range(12)]
good = [d for d in dists if d > 0]
print({"bytes": len(buf), "packets": len(pk), "packets_per_s": round(len(pk)/3, 1),
       "rotation_deg_per_s_median": sorted(speeds)[len(speeds)//2] if speeds else None,
       "valid_points": len(good), "range_mm_min_max": (min(good), max(good)) if good else None})
