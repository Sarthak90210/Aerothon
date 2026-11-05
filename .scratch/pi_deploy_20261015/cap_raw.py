import os, termios, time, collections
fd = os.open('/dev/ttyUSB0', os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
a = termios.tcgetattr(fd); a[0] = 0; a[1] = 0; a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL; a[3] = 0
a[4] = a[5] = termios.B230400; termios.tcsetattr(fd, termios.TCSANOW, a)
buf = b""; t0 = time.time(); marks = []
while time.time() - t0 < 8:
    try:
        chunk = os.read(fd, 8192); buf += chunk
    except BlockingIOError:
        time.sleep(0.02)
    marks.append(len(buf))
os.close(fd)
per_s = [marks[min(len(marks)-1, int(i*len(marks)/8))] for i in range(1, 9)]
c = collections.Counter(buf).most_common(6)
print({'bytes': len(buf), 'cumulative_per_s': per_s, 'top_bytes': [(hex(b), n) for b, n in c],
       'ld06_headers': sum(1 for i in range(len(buf)-1) if buf[i] == 0x54 and buf[i+1] == 0x2C)})
