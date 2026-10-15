"""Receipt rate and capture age for display; never flight decision inputs."""
import math
import time
from collections import deque


class SensorMetric:
    def __init__(self):
        self.receipts = deque(maxlen=120)
        self.capture = None

    def observe(self, header):
        self.receipts.append(time.monotonic())
        self.capture = header.stamp.sec + header.stamp.nanosec / 1e9

    def snapshot(self, clock, now=None):
        now = time.monotonic() if now is None else now
        stamps = [t for t in self.receipts if now - t < 3.0]
        hz = (len(stamps) - 1) / (stamps[-1] - stamps[0]) if len(stamps) > 1 and stamps[-1] > stamps[0] else None
        receipt_age = max(0., now - self.receipts[-1]) if self.receipts else None
        capture_age = clock - self.capture if clock is not None and self.capture is not None else None
        if capture_age is not None and (not math.isfinite(capture_age) or capture_age < 0 or self.capture <= 0):
            capture_age = None
        return dict(ok=receipt_age is not None and receipt_age < 3 and capture_age is not None and capture_age < 3,
                    hz=hz, receipt_age_s=receipt_age, capture_age_s=capture_age)
