"""Bounded observation pause at a measured stop anchor, before gate handover."""
import math
from gate_advance_braking_candidate_20261007 import BrakedGateAdvance,RUNNING


class ObservationPausedGateAdvance(BrakedGateAdvance):
    def __init__(self,*args,observation_pause_s=1.,**kwargs):
        super().__init__(*args,**kwargs)
        if not math.isfinite(observation_pause_s) or observation_pause_s<=0:
            raise ValueError('Observation pause must be finite and positive')
        self.observation_pause_s=float(observation_pause_s)

    def initialise(self):
        super().initialise()
        self._observation_wait_started=None

    def update(self):
        if self._fresh_motion(self._now()) is not None:
            self._observation_wait_started=None
        return super().update()

    def _fail(self,reason):
        if reason=='fresh pose, velocity and lidar capture times required':
            now=self._now()
            if self._observation_wait_started is None:
                self._observation_wait_started=now
            self._settle_first=self._settle_last=None
            self._settle_count=0
            elapsed=now-self._observation_wait_started
            if 0<=elapsed<=self.observation_pause_s:
                self.feedback_message='holding measured gate position while awaiting fresh captures'
                return RUNNING
            reason='fresh observations did not recover during bounded gate hold'
        return super()._fail(reason)
