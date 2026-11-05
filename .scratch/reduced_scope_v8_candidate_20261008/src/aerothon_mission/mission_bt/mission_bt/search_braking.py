"""Stop an invalidated search segment, then replan from fresh measured pose."""
import math


class SearchBrakingGate:
    def __init__(self):
        self.hold = None
        self.last_velocity_stamp = None
        self.settled_samples = 0

    def tick(self, stage):
        mav = stage.mav
        current = stage._current_exclusions()
        goal = getattr(stage, '_streamed_search_goal', None)
        commanded = getattr(mav, 'position_target_xy', None)
        if callable(commanded):
            goal = commanded()
        # Share the router's segment certificate, including its narrow
        # nearest-edge escape when already inside an inflated margin. A
        # blanket intersection check cancels that escape and brakes there.
        if self.hold is None and goal is not None and (
                not all(math.isfinite(v) for v in goal)
                or not stage.router._segment_safe(mav, goal, exclusions=current)):
            self.hold = (*mav.pos(), mav.yaw())
            self.last_velocity_stamp = None
            self.settled_samples = 0
            stage.router.reset()
            mav.log('search segment invalidated by observed exclusion; braking before replanning')
        if self.hold is None:
            return False
        mav.goto(*self.hold)
        stage.feedback_message = 'braking invalidated segment; waiting for fresh settled FCU motion'
        now = stage.clock_fn() if callable(stage.clock_fn) else None
        inputs = getattr(mav, 'delivery_inputs', {})
        try:
            pose_stamp = float(inputs['pose_stamp'])
            stamp = float(inputs['velocity_stamp'])
            speed = float(inputs['speed'])
            fresh = (now is not None and all(math.isfinite(x) for x in (pose_stamp, stamp, speed, now))
                     and 0 <= now-pose_stamp <= .5 and 0 <= now-stamp <= .5 and speed >= 0.)
        except (KeyError, TypeError, ValueError):
            fresh = False
        if not fresh or speed > .1:
            self.settled_samples = 0
            self.last_velocity_stamp = None
            return True
        if self.last_velocity_stamp is None or stamp > self.last_velocity_stamp:
            self.settled_samples += 1
            self.last_velocity_stamp = stamp
        if self.settled_samples < 3:
            return True
        # The replan reads mav.pos() now. The braking target is not a measured
        # arrival position, and three copies of one velocity sample are not
        # independent evidence that the aircraft has stopped.
        stage._replan_mid_sweep()
        stage._streamed_search_goal = None
        self.hold = None
        self.last_velocity_stamp = None
        self.settled_samples = 0
        return True
