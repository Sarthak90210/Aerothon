"""Centre confirmed clipped lettering without deriving range from its area."""
import math
import py_trees
from mission_bt.mission_tree import FindReturnBanner, bearing_to_angle


class FramedReturnBanner(FindReturnBanner):
    def initialise(self):
        super().initialise()
        self._clip_seen = set()
        self._clip_key = None
        self._clip_samples = 0
        self._clip_sequence = None
        self._focus = None

    def update(self):
        if self.phase == 'clipped_focus':
            focus = self._focus
            self.mav.goto(*self.here, self._cur_alt, focus['yaw'])
            camera_ok = self.mav.camera_settled(self._look)
            yaw_ok = abs(self._wrap(self.mav.yaw()-focus['yaw'])) <= self.yaw_tol
            if camera_ok and yaw_ok:
                self.phase = 'sweep'
                self._since = self.clock()
                self._turning = False
                self._hits = 0
                self._last_banner_sample = None
            elif self.clock()-focus['start'] > max(self.camera_timeout_s, self.turn_timeout_s):
                # Retain the original heading/tilt if this bounded camera
                # correction cannot settle. No clipped range is admitted.
                self.headings[self.hi] = focus['previous_yaw']
                self._look = focus['previous_look']
                self._camera(self._look)
                self.phase = 'sweep'
                self._begin_heading()
            return py_trees.common.Status.RUNNING
        if self.phase == 'sweep' and not self._turning and self.hi < len(self.headings):
            observe = getattr(self.mav, 'banner_observation', None)
            observation = observe() if callable(observe) else None
            key = (tuple(round(v, 1) for v in self.here), self.hi)
            if key != self._clip_key:
                self._clip_key = key
                self._clip_samples = 0
                self._clip_sequence = None
            fresh_clip = (observation is not None and observation.get('identified') is True
                and getattr(self.mav, 'banner_clipped', False)
                and self._since is not None and observation['capture_stamp'] >= self._since)
            if not fresh_clip:
                self._clip_samples = 0
            elif key not in self._clip_seen and observation['sequence'] != self._clip_sequence:
                self._clip_sequence = observation['sequence']
                self._clip_samples += 1
                if self._clip_samples >= max(3, self.hits_needed):
                    self._clip_seen.add(key)
                    yaw = observation['pose']['yaw'] + bearing_to_angle(observation['bearing'], self.hfov)
                    self._focus = dict(yaw=self._wrap(yaw), start=self.clock(),
                                       previous_yaw=self.headings[self.hi], previous_look=self._look)
                    self.headings[self.hi] = self._focus['yaw']
                    box = observation.get('board_px')
                    height = (observation.get('image_wh') or [1280, 720])[1]
                    if box and box[1] <= 1 and self._look == 'BANNER':
                        self._look = 'FORWARD'
                    elif (box and box[1]+box[3] >= height-1 and self._look == 'FORWARD'
                            and self._cur_alt > self.orbit_alt_m + .3):
                        self._look = 'BANNER'
                    self._camera(self._look)
                    self.phase = 'clipped_focus'
                    self.mav.log('FindReturnBanner: distinct clipped lettering captures; centring captured bearing before any range assessment')
                    return py_trees.common.Status.RUNNING
        return super().update()
