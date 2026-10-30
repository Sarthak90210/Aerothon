"""Square fiducial markers (ArUco / AprilTag) through OpenCV's aruco module.

The field's markers are not QR codes. Photographed at the venue on 29 Oct
2026 they are AprilTag 36h11 tags (OpenCV DICT_APRILTAG_36h11), IDs 100, 200,
300, 400 and 500 read off the boards, each a black-bordered 8 x 8 cell tag
on a white board whose margin is about one cell. The tag's ID is its
pattern: two boards that look alike carry the same ID, so the ID read here is
both the payload and the appearance the mission matches on.

TagDecoder.read() keeps QrDecoder's contract -- ([(payload, quad)], unread
quad or None), quads 4x2 float32 image corners -- so qr_node and the mission
behind it are unchanged: the payload is the tag ID in decimal ("300").

A candidate square the detector found but could not identify (motion blur,
vibration) is returned as unread when it looks like a tag seen from above:
near-square (MAX_SIDE_RATIO), at least UNREAD_MIN_PX across, a dark outer
cell ring round an interior holding both tones. The mission then holds over
it (DecodeHover) until the blur goes. Paving joints and shadows also make
dark quadrilaterals; the ring test is what keeps them out.

OpenCV 4.6 (Ubuntu 24.04, the Pi's container) has only the module-level
detectMarkers; 4.7 and later have ArucoDetector. Both are supported.
"""

import cv2
import numpy as np

try:
    from cv2 import aruco
except ImportError:                 # an OpenCV build without the contrib module
    aruco = None


DEFAULT_DICTIONARY = "DICT_APRILTAG_36h11"
# OpenCV keeps only the larger of two candidates whose corners lie within
# this share of the perimeter (default 0.05). A white board on darker ground
# thresholds to a dark band round the board, a candidate a margin bigger than
# the tag inside it, and the tag was the one dropped: flat-shaded, 48 of 224
# synthetic boards from 24 to 360 px went unread, 0 at 0.02; the six field
# photographs read at either.
MIN_MARKER_DISTANCE_RATE = 0.02
MAX_SIDE_RATIO = 1.4        # longest side / shortest, a nadir view of a square
UNREAD_MIN_PX = 24          # smaller unidentified squares are not held over
MIN_CONTRAST = 60           # grey levels between the patch's 10th and 90th percentiles
RING_MAX_LIGHT = 0.2        # share of the black border ring that may read light
INNER_LIGHT = (0.1, 0.9)    # share of the data cells that read light


def available():
    return aruco is not None


def dictionary(name):
    """The predefined dictionary called `name`, matched case-insensitively
    (OpenCV 4.6 spells DICT_APRILTAG_36h11 both ways, later versions one)."""
    if aruco is None:
        raise RuntimeError("OpenCV has no aruco module (opencv-contrib)")
    wanted = str(name).strip().upper()
    for attr in dir(aruco):
        if attr.startswith("DICT_") and attr.upper() == wanted:
            return aruco.getPredefinedDictionary(getattr(aruco, attr))
    raise ValueError(f"unknown marker dictionary {name!r}")


def marker_cells(name, marker_id):
    """The tag's cells, black border included, as rows of booleans (True
    black): what the simulator prints and the tests render."""
    d = dictionary(name)
    n = int(d.markerSize) + 2
    if hasattr(aruco, "generateImageMarker"):
        img = aruco.generateImageMarker(d, int(marker_id), n, borderBits=1)
    else:
        img = aruco.drawMarker(d, int(marker_id), n, borderBits=1)
    return [[bool(v < 128) for v in row] for row in img]


class TagDecoder:
    def __init__(self, dictionary_name=DEFAULT_DICTIONARY):
        self.name = str(dictionary_name)
        self._dict = dictionary(self.name)
        self.cells = int(self._dict.markerSize) + 2
        if hasattr(aruco, "ArucoDetector"):
            params = aruco.DetectorParameters()
            params.minMarkerDistanceRate = MIN_MARKER_DISTANCE_RATE
            detector = aruco.ArucoDetector(self._dict, params)
            self._detect = detector.detectMarkers
        else:
            params = aruco.DetectorParameters_create()
            params.minMarkerDistanceRate = MIN_MARKER_DISTANCE_RATE
            self._detect = lambda gray: aruco.detectMarkers(
                gray, self._dict, parameters=params)

    def read(self, bgr):
        """([(payload, quad)], unread quad or None); payload is the tag ID."""
        gray = bgr if bgr.ndim == 2 else cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        corners, ids, rejected = self._detect(gray)
        found = []
        if ids is not None:
            for quad, marker_id in zip(corners, ids.flatten()):
                found.append((str(int(marker_id)), quad.reshape(4, 2).astype(np.float32)))
        if found:
            return _distinct(found), None
        return [], self._unread(gray, rejected)

    def _unread(self, gray, rejected):
        best, best_px = None, 0.0
        for cand in rejected if rejected is not None else ():
            quad = np.asarray(cand, np.float32).reshape(4, 2)
            px = float(np.ptp(quad, axis=0).max())
            if px < UNREAD_MIN_PX or px <= best_px or not _square(quad):
                continue
            if self._tag_like(gray, quad):
                best, best_px = quad, px
        return best

    def _tag_like(self, gray, quad):
        """A dark outer cell ring round an interior holding both tones."""
        n, per = self.cells, 8
        side = n * per
        dst = np.float32([[0, 0], [side, 0], [side, side], [0, side]])
        warp = cv2.warpPerspective(
            gray, cv2.getPerspectiveTransform(quad, dst), (side, side))
        lo, hi = np.percentile(warp, (10, 90))
        if hi - lo < MIN_CONTRAST:
            return False
        light = warp > (lo + hi) / 2.0
        # Each cell's centre only: the edges blur into their neighbours.
        m = per // 4
        cell = light.reshape(n, per, n, per)[:, m:per - m, :, m:per - m].mean(axis=(1, 3))
        ring = np.concatenate([cell[0], cell[-1], cell[1:-1, 0], cell[1:-1, -1]])
        inner = float(cell[1:-1, 1:-1].mean())
        return float(ring.mean()) <= RING_MAX_LIGHT and INNER_LIGHT[0] <= inner <= INNER_LIGHT[1]


def _distinct(found):
    """One reading per tag, the largest: at MIN_MARKER_DISTANCE_RATE a tag can
    come back twice, from two contours of its own border. Two boards with one
    ID stay two."""
    out = []
    for payload, quad in sorted(found, key=lambda f: -float(np.ptp(f[1], axis=0).max())):
        centre = quad.mean(axis=0)
        if not any(p == payload and np.linalg.norm(q.mean(axis=0) - centre)
                   < 0.5 * float(np.ptp(q, axis=0).max()) for p, q in out):
            out.append((payload, quad))
    return out


def _square(quad):
    sides = np.linalg.norm(np.roll(quad, -1, axis=0) - quad, axis=1)
    return sides.min() > 0 and sides.max() / sides.min() <= MAX_SIDE_RATIO
