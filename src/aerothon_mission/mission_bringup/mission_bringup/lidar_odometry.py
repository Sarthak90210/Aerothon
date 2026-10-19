"""Local 2D scan odometry for mapping. Never supplies flight-navigation pose."""
import math

import numpy as np
from scipy.spatial import cKDTree


def rotation(yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([[c, -s], [s, c]])


def transform(points, pose):
    return points @ rotation(pose[2]).T + pose[:2]


def match_scan(reference, current, initial=(0., 0., 0.), recovery=False):
    """Trimmed robust point-to-line ICP, with overlap and observability gates.

    The alignment gate scales with the reference scan's measured scatter about
    its local wall lines, so a noisy real sensor is held to its own noise floor
    instead of a fixed figure only a clean simulated scan can meet.
    """
    if len(reference) < 80 or len(current) < 80:
        raise ValueError('need at least 80 valid scene returns')
    tree = cKDTree(reference)
    _, neighbours = tree.query(reference, k=7)
    local = reference[neighbours]
    centred = local - local.mean(axis=1, keepdims=True)
    values, vectors = np.linalg.eigh(np.einsum('nki,nkj->nij', centred, centred))
    normals = vectors[:, :, 0]
    line = values[:, 0] < .15 * np.maximum(values[:, 1], 1e-9)
    # Seven-point line fits leave five residual degrees of freedom.
    scatter = float(np.sqrt(np.median(values[line, 0]) / 5)) if line.any() else 0.
    pair_noise = math.sqrt(2) * scatter
    rmse_gate = max(.02, min(.04, 1.5*pair_noise)) if recovery else max(.04, min(.08, 2*pair_noise))
    pose = np.array(initial, dtype=float)
    converged = False
    for _ in range(40):
        rotated = current @ rotation(pose[2]).T
        moved = rotated + pose[:2]
        distance, nearest = tree.query(moved)
        valid = (distance < .35) & line[nearest]
        if valid.sum() < 60 or valid.mean() < .5:
            raise ValueError('insufficient overlap; mapping held')
        p, n, q = rotated[valid], normals[nearest[valid]], reference[nearest[valid]]
        error = np.einsum('ij,ij->i', n, moved[valid] - q)
        cutoff = max(.012, float(np.quantile(abs(error), .8)))
        keep = abs(error) <= cutoff
        p, n, error = p[keep], n[keep], error[keep]
        A = np.column_stack((n[:, 0], n[:, 1], -n[:, 0]*p[:, 1] + n[:, 1]*p[:, 0]))
        normalised = A / np.maximum(np.linalg.norm(A, axis=0), 1e-9)
        eigenvalues = np.linalg.eigvalsh(normalised.T @ normalised)
        if eigenvalues[0] < .002 * eigenvalues[-1]:
            raise ValueError('scene cannot constrain translation and yaw; need corners or nonparallel walls')
        weight = np.minimum(1., .025 / np.maximum(abs(error), 1e-8))
        delta = np.linalg.lstsq(A * np.sqrt(weight[:, None]), -error*np.sqrt(weight), rcond=None)[0]
        if np.linalg.norm(delta[:2]) > .25 or abs(delta[2]) > math.radians(10):
            raise ValueError('registration step too large; mapping held')
        pose += delta
        # Trimming can leave a sub-millimetre limit cycle on noisy scans.
        if np.linalg.norm(delta[:2]) < .001 and abs(delta[2]) < .0005:
            converged = True
            break
    if not converged:
        raise ValueError('scan matching did not converge; mapping held')
    moved = transform(current, pose)
    distances, nearest = tree.query(moved)
    use = (distances < .15) & line[nearest]
    if use.mean() < .55:
        raise ValueError('too few consistent returns; mapping held')
    residual = np.einsum('ij,ij->i', normals[nearest[use]], moved[use]-reference[nearest[use]])
    rmse = float(np.sqrt(np.mean(np.minimum(residual**2, .15**2))))
    if rmse > rmse_gate:
        raise ValueError(f'scan alignment error exceeds {rmse_gate*1000:.0f} mm noise gate; mapping held')
    return pose, {'rmse_m': rmse, 'noise_m': pair_noise, 'overlap': float(use.mean()), 'returns': int(len(current))}


def compose(base, step):
    return np.r_[base[:2] + rotation(base[2]) @ step[:2], base[2] + step[2]]


def relative_to(base, pose):
    return np.r_[rotation(-base[2]) @ (pose[:2] - base[:2]), pose[2] - base[2]]


class ScanOdometry:
    """Keyframe scan odometry whose accepted poses always rest on a registration.

    While held, raw scans dead-reckon a predicted pose by registering each one
    against the newest held scan that itself registered (the anchor), or else
    against the previous scan, whose pose was carried at constant velocity, so
    one unregistrable scan does not break the chain. The prediction
    seeds re-registration against the validated keyframe and bounds how far
    that registration may land. If the current scan registered and the chain
    holds at most one constant-velocity scan, it is ordinary scan-to-scan
    odometry and may resume tracking once
    its average speed since the last accepted pose is within the motion bound;
    this covers drift that carries the aircraft out of the keyframe's view.
    A capture gap, an anchor older than a second or too much accumulated
    uncertainty drops the prediction, leaving the strict revalidation against
    the last pose.
    """
    LOST_UNCERTAINTY_M = 1.
    # Constant-velocity scans a chain may contain and still resume tracking.
    CHAIN_INTERPOLATED_SCANS = 1

    def __init__(self):
        self.reference = None
        self.reference_pose = np.zeros(3)
        self.relative = np.zeros(3)
        self.pose = np.zeros(3)
        self.rate = np.zeros(3)
        self.stamp = None
        self.input_stamp = None
        self.recovering = False
        self.previous = None
        self.held = False
        self.predicted = np.zeros(3)
        self.uncertainty = (0., 0.)
        self.anchor = self.last = None
        self.interpolated = 0

    def update(self, points, stamp):
        points = np.asarray(points, dtype=float)
        if points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all() or len(points) < 80:
            raise ValueError('need at least 80 finite scene points')
        if not math.isfinite(stamp) or stamp <= 0:
            raise ValueError('invalid capture timestamp')
        # Limit registration work without changing the published full scan.
        if len(points) > 720:
            points = points[::math.ceil(len(points)/720)]
        if self.reference is None:
            # Self-registration proves the initial scene constrains all 3 DOF.
            _, quality = match_scan(points, points)
            self.reference = self.previous = points.copy()
            self.stamp = stamp
            self.input_stamp = stamp
            return self.pose.copy(), quality
        input_dt = stamp - self.input_stamp
        if input_dt <= 0:
            raise ValueError('capture clock reset; restart mapping to establish a new local origin')
        previous, self.previous, self.input_stamp = self.previous, points.copy(), stamp
        if input_dt > 1.:
            self.recovering = self.held = True
            self.uncertainty = None
            raise ValueError('capture gap; map held until consecutive scans revalidate the previous scene')
        chained = self._dead_reckon(points, stamp) if self.held else None
        self.recovering = self.recovering or stamp-self.stamp > 1.
        seed = relative_to(self.reference_pose, self.predicted) if self.held and self.uncertainty else self.relative
        try:
            try:
                relative, quality = match_scan(self.reference, points, seed, recovery=self.recovering)
                pose, keyframe = compose(self.reference_pose, relative), False
                self._check_plausible(pose, quality, input_dt, stamp)
            except ValueError:
                if not self.held:
                    # The keyframe no longer registers, but the previous scan was
                    # accepted, so its pose is known: continue from it instead.
                    step, quality = match_scan(previous, points, self.rate*input_dt)
                    pose, relative, keyframe = compose(self.pose, step), np.zeros(3), True
                    self._check_plausible(pose, quality, input_dt, stamp)
                elif chained is None or self.interpolated > self.CHAIN_INTERPOLATED_SCANS:
                    raise
                else:
                    pose, quality, relative, keyframe = self.predicted.copy(), chained, np.zeros(3), True
                    self._check_average_speed(pose, stamp)
        except ValueError:
            if not self.held:
                self.held, self.uncertainty, self.interpolated = True, (0., 0.), 0
                self.anchor = self.last = (previous, self.pose.copy(), self.stamp, (0., 0.), 0)
                self._dead_reckon(points, stamp)
            raise
        self.rate = relative_to(self.pose, pose) / (stamp - self.stamp)
        self.pose, self.relative, self.stamp = pose, relative, stamp
        self.recovering = self.held = False
        self.predicted, self.uncertainty, self.anchor, self.last = pose.copy(), (0., 0.), None, None
        if keyframe or np.linalg.norm(relative[:2]) > .3 or abs(relative[2]) > .2:
            self.reference, self.reference_pose, self.relative = points.copy(), pose.copy(), np.zeros(3)
        return pose.copy(), quality

    def _dead_reckon(self, points, stamp):
        """Advance the held prediction; return the quality if this scan registered."""
        if self.uncertainty is None:
            return None
        for base in (self.anchor,) if self.last is self.anchor else (self.anchor, self.last):
            base_points, base_pose, base_stamp, (xy, yaw), interpolated = base
            dt = stamp - base_stamp
            if dt > 1.:
                continue
            try:
                step, quality = match_scan(base_points, points, self.rate*dt)
            except ValueError:
                continue
            xy, yaw = xy + .005 + .1*np.linalg.norm(step[:2]), yaw + math.radians(.1) + .1*abs(step[2])
            if xy > self.LOST_UNCERTAINTY_M:
                continue
            self.rate = step / dt
            self.predicted, self.uncertainty, self.interpolated = compose(base_pose, step), (xy, yaw), interpolated
            self.anchor = self.last = (points, self.predicted.copy(), stamp, self.uncertainty, interpolated)
            return quality
        # Unregistered scan: constant velocity from the anchor, bounded speed.
        _, anchor_pose, anchor_stamp, (xy, yaw), interpolated = self.anchor
        dt = stamp - anchor_stamp
        xy, yaw = xy + 2*dt + .03, yaw + math.radians(90)*dt + .03
        if dt > 1. or xy > self.LOST_UNCERTAINTY_M:
            self.uncertainty = None
            return None
        self.predicted, self.uncertainty = compose(anchor_pose, self.rate*dt), (xy, yaw)
        self.last = (points, self.predicted.copy(), stamp, self.uncertainty, interpolated + 1)
        return None

    def _check_plausible(self, pose, quality, input_dt, stamp):
        if self.recovering and quality['overlap'] < .8:
            raise ValueError('lost scene is not revalidated; restart mapping at a new origin')
        if self.held and self.uncertainty:
            xy, yaw = self.uncertainty
            if (np.linalg.norm(pose[:2]-self.predicted[:2]) > .15 + xy or
                    abs(pose[2]-self.predicted[2]) > math.radians(3) + yaw):
                raise ValueError('re-registration disagrees with held dead reckoning; mapping held')
            self._check_average_speed(pose, stamp)
            return
        if self.recovering and (np.linalg.norm(pose[:2]-self.pose[:2]) > .15 or
                                abs(pose[2]-self.pose[2]) > math.radians(3)):
            raise ValueError('lost scene is not revalidated; restart mapping at a new origin')
        dt = input_dt if not self.held else min(.3, stamp - self.stamp)
        if np.linalg.norm(pose[:2] - self.pose[:2]) > 2*dt + .03 or abs(pose[2]-self.pose[2]) > math.radians(90)*dt + .03:
            raise ValueError('motion exceeds scan-matching bound; mapping held')

    def _check_average_speed(self, pose, stamp):
        elapsed = stamp - self.stamp
        if (np.linalg.norm(pose[:2]-self.pose[:2]) > 2*elapsed + .03 or
                abs(pose[2]-self.pose[2]) > math.radians(90)*elapsed + .03):
            raise ValueError('held motion exceeds scan-matching bound; mapping held')
