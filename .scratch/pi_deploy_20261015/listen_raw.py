import os, sys, termios, time
dev = sys.argv[1]
rates = {115200: termios.B115200, 230400: termios.B230400, 460800: termios.B460800, 921600: termios.B921600}
for baud in (230400, 115200, 921600):
    fd = os.open(dev, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
    a = termios.tcgetattr(fd); a[0] = 0; a[1] = 0; a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL; a[3] = 0
    a[4] = a[5] = rates[baud]; termios.tcsetattr(fd, termios.TCSANOW, a)
    buf = b""; t0 = time.time()
    while time.time() - t0 < 2:
        try: buf += os.read(fd, 8192)
        except BlockingIOError: time.sleep(0.01)
    os.close(fd)
    print({"baud": baud, "bytes": len(buf), "head": buf[:16].hex()})
