"""Candidate gate speed lease; no simulator imports or geometric truth inputs."""
import math

import py_trees
from mission_bt.mission_tree import GateAdvance

RUNNING = py_trees.common.Status.RUNNING
FAILURE = py_trees.common.Status.FAILURE
SUCCESS = py_trees.common.Status.SUCCESS


class BrakedGateAdvance(GateAdvance):
    """Keep position control until fresh measurements show a settled aircraft.

    The fixed cap is a simulation calibration candidate. Native qualification
    and hardware rate/response qualification remain necessary before adoption.
    """

    def __init__(self, *args, gate_speed_mps=.35, arrival_speed_mps=.08,
                 settle_s=.3, stale_s=.3, service_timeout_s=3., **kwargs):
        super().__init__(*args, **kwargs)
        values = (gate_speed_mps, arrival_speed_mps, stale_s, service_timeout_s)
        if not all(math.isfinite(value) and value > 0 for value in values):
            raise ValueError('Gate braking parameters must be finite and positive')
        if not math.isfinite(settle_s) or settle_s < 0:
            raise ValueError('Invalid gate settling duration')
        self.gate_speed_mps = float(gate_speed_mps)
        self.arrival_speed_mps = float(arrival_speed_mps)
        self.settle_s = float(settle_s)
        self.stale_s = float(stale_s)
        self.service_timeout_s = float(service_timeout_s)

    def initialise(self):
        super().initialise()
        self._phase = 'ADMIT'
        self._entry_speed = getattr(self.mav, 'speed_cmd', None)
        self._lease_future = None
        self._lease_sent = None
        self._hold = None
        self._settle_first = None
        self._settle_last = None
        self._settle_count = 0
        self._started = self._now()

    def _now(self):
        return self.mav.node.get_clock().now().nanoseconds * 1e-9

    def _fresh_motion(self, now):
        inputs = getattr(self.mav, 'delivery_inputs', {})
        pose_stamp = inputs.get('pose_stamp')
        velocity_stamp = inputs.get('velocity_stamp')
        speed = inputs.get('speed')
        scan = getattr(self.mav, '_scan', None)
        if scan is None:
            return None
        scan_stamp = scan.header.stamp.sec + scan.header.stamp.nanosec * 1e-9
        stamps = (pose_stamp, velocity_stamp, scan_stamp)
        if not all(isinstance(stamp, (int, float)) and math.isfinite(stamp)
                   and 0 <= now-stamp <= self.stale_s for stamp in stamps):
            return None
        if not isinstance(speed, (int, float)) or not math.isfinite(speed) or speed < 0:
            return None
        return float(speed), float(velocity_stamp)

    def _hold_position(self):
        self.mav.goto(*self._hold, self.mav.yaw())

    def _fail(self, reason):
        self.feedback_message = self.mav.abort_reason = 'GateAdvance: ' + reason
        return FAILURE

    def _speed_ack(self, speed, now):
        if self._lease_future is None:
            try:
                future = self.mav.set_speed(speed)
            except Exception:
                return self._fail('ground-speed command service failed')
            if future is None:
                return self._fail('ground-speed command service unavailable')
            self._lease_future = future
            self._lease_sent = now
        if not self._lease_future.done():
            if now-self._lease_sent > self.service_timeout_s:
                return self._fail('ground-speed command acknowledgement timed out')
            return RUNNING
        try:
            accepted = bool(self._lease_future.result().success)
        except Exception:
            accepted = False
        if not accepted:
            return self._fail('flight controller rejected the ground-speed command')
        self._lease_future = None
        self._lease_sent = None
        return SUCCESS

    def update(self):
        now = self._now()
        if self._hold is None:
            self._hold = self.mav.pos()
        # Refresh the stop anchor from an actual fresh pose even if another
        # observation has failed. A stale scan must not command a return to
        # the original gate approach after the aircraft has crossed it.
        pose_stamp = getattr(self.mav, 'delivery_inputs', {}).get('pose_stamp')
        if isinstance(pose_stamp, (int, float)) and math.isfinite(pose_stamp) and (
                0 <= now-pose_stamp <= self.stale_s):
            position = self.mav.pos()
            if all(math.isfinite(value) for value in position):
                self._hold = position
        if now-self._started > 60.:
            self._hold_position()
            return self._fail('gate crossing or braking did not settle in 60 seconds')
        motion = self._fresh_motion(now)
        if motion is None:
            self._hold_position()
            return self._fail('fresh pose, velocity and lidar capture times required')
        speed, velocity_stamp = motion

        if self._phase == 'ADMIT':
            self._hold_position()
            if not isinstance(self._entry_speed, (int, float)) or not (
                    math.isfinite(self._entry_speed) and self._entry_speed > 0):
                return self._fail('previous commanded navigation speed is unavailable')
            status = self._speed_ack(self.gate_speed_mps, now)
            if status != SUCCESS:
                return status
            self._phase = 'CROSS'

        if self._phase == 'CROSS':
            status = super().update()
            if status != SUCCESS:
                return status
            # The original leaf returns on distance alone. Keep its routed
            # position target active while measuring actual braking instead.
            self.router.fly(self.mav, *self._target, self._flight_alt, self.mav.yaw())
            if speed > self.arrival_speed_mps:
                self._settle_first = self._settle_last = None
                self._settle_count = 0
                self.feedback_message = 'waiting for measured gate braking'
                return RUNNING
            if self._settle_last != velocity_stamp:
                if self._settle_first is None:
                    self._settle_first = velocity_stamp
                self._settle_last = velocity_stamp
                self._settle_count += 1
            if self._settle_count < 3 or velocity_stamp-self._settle_first < self.settle_s:
                self.feedback_message = 'confirming gate braking with distinct FCU samples'
                return RUNNING
            self._hold = self.mav.pos()
            self._phase = 'RESTORE'

        if self._phase == 'RESTORE':
            self._hold_position()
            status = self._speed_ack(float(self._entry_speed), now)
            if status != SUCCESS:
                return status
            self._phase = 'READY'

        self._hold_position()
        if speed > self.arrival_speed_mps:
            self.feedback_message = 'waiting for the restored-speed position hold to settle'
            return RUNNING
        return SUCCESS
