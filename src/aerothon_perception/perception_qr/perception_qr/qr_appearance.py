"""Match a QR by how it LOOKS, not by what it says.

WHY THIS EXISTS

    The organisers confirmed the start marker is 1 m square with a 3-inch
    white border, and that it is NOT settled whether the codes carry any
    encoded data at all. The requirement is that the aircraft "identify and
    match the QR code based on its visual appearance (image matching),
    without relying on decoded information".

    Decoding was the only identification the stack had. A code that carries
    nothing decodes to nothing, so on the day that path can return no
    evidence at all while the marker sits squarely in frame. This supplies
    the primary evidence instead: the pad marker whose PATTERN is the one the
    start marker showed. A decoded payload, when there is one, then confirms
    it (`qr_match.matches`).

HOW

    A located marker is rectified off its own four corners -- the finder
    patterns give the orientation -- to a fixed square, blurred slightly,
    and reduced to a coarse bit grid. Comparison is the fraction of agreeing
    cells, taken as the best of the four 90-degree rotations, because a code
    photographed from the other side of a pad is the same code turned round.

    Deliberately coarse. A per-pixel comparison of two camera frames at
    different ranges, exposures and angles measures the camera, not the code;
    a 16x16 occupancy grid measures the pattern. The threshold is set well
    clear of what two DIFFERENT codes score, which `sim/test_qr_appearance.py`
    pins against the real generated markers.
"""

import numpy as np

GRID = 16                 # cells a side; a 1 m marker is ~25 modules across
MIN_SIDE_PX = 24          # below this a rectified marker is mush
DEFAULT_THRESHOLD = 0.82  # agreeing cells needed to call it the same pattern


def _order(quad):
    """The four corners as top-left, top-right, bottom-right, bottom-left."""
    pts = np.asarray(quad, dtype=np.float32).reshape(4, 2)
    middle = pts.mean(axis=0)
    angles = np.arctan2(pts[:, 1]-middle[1], pts[:, 0]-middle[0])
    # Sorting by angle gives a consistent winding; rotate so the corner
    # nearest the top-left of the frame comes first.
    order = np.argsort(angles)
    pts = pts[order]
    start = int(np.argmin(pts.sum(axis=1)))
    return np.roll(pts, -start, axis=0)


def signature(bgr, quad, grid=GRID):
    """A located marker as a coarse bit grid, or None if it is unusable."""
    import cv2
    pts = _order(quad)
    side = int(max(np.linalg.norm(pts[0]-pts[1]), np.linalg.norm(pts[1]-pts[2])))
    if side < MIN_SIDE_PX:
        return None
    target = np.array([[0, 0], [side-1, 0], [side-1, side-1], [0, side-1]],
                      dtype=np.float32)
    transform = cv2.getPerspectiveTransform(pts.astype(np.float32), target)
    flat = cv2.warpPerspective(bgr, transform, (side, side))
    grey = cv2.cvtColor(flat, cv2.COLOR_BGR2GRAY) if flat.ndim == 3 else flat
    grey = cv2.GaussianBlur(grey, (3, 3), 0)
    cells = cv2.resize(grey, (grid, grid), interpolation=cv2.INTER_AREA)
    # Threshold against the marker's own mean: a code read in shade is the
    # same code, and an absolute level would be an assumption about the light.
    return (cells < float(cells.mean())).astype(np.uint8)


def agreement(left, right):
    """Fraction of agreeing cells, over the four rotations. 0.0 if either is None."""
    if left is None or right is None:
        return 0.0
    best = 0.0
    turned = right
    for _ in range(4):
        best = max(best, float(np.mean(left == turned)))
        turned = np.rot90(turned)
    return round(best, 4)


def same_marker(left, right, threshold=DEFAULT_THRESHOLD):
    """Whether two signatures are the same printed pattern."""
    score = agreement(left, right)
    return score >= float(threshold), score
