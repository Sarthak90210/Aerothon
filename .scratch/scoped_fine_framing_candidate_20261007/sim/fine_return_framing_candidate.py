"""Isolated return reacquisition: finer yaw before leaving an observed standoff."""
import math
from mission_bt.mission_tree import AlignToBanner


class FineReturnFraming(AlignToBanner):
    def _reset_recovery(self):
        super()._reset_recovery()
        self._fine_return_attempted = False

    def _give_up(self):
        if (getattr(self.mav, 'outbound_banner_xy', None) is not None
                and not self._fine_return_attempted and self._relocations == 0
                and self._good_vantage is None):
            self._fine_return_attempted = True
            x, y, z = self.mav.pos()
            # Return search may leave the level camera selected. At the high
            # identification altitude it can crop a nearby board vertically.
            if self.alt_floor_m is not None and z > self.alt_floor_m + .3:
                self.mav.set_camera_pose('BANNER')
            yaw = self._entry_yaw if self._entry_yaw is not None else self._sweep_origin
            self.mav.log('AlignToBanner: return coarse sweep empty; one fine yaw sweep at the same measured position before relocation')
            return self._restart_sweep_at(x, y, z, yaw,
                offsets=self._zigzag_offsets(math.radians(15), 24), guard=False)
        return super()._give_up()
