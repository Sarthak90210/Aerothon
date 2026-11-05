"""Candidate: retain a valid camera vantage when an area range is uncertain."""
import math
import py_trees
from mission_bt.mission_tree import FindReturnBanner


class ObservedVantageReturnBanner(FindReturnBanner):
    def _found(self, bx, by, th, rng):
        x, y = self.mav.pos()[:2]
        normal = self._inward_normal(bx, by)
        if normal is not None:
            ax = bx+self.standoff_m*normal[0]
            ay = by+self.standoff_m*normal[1]
            if not self._zone_side(ax, ay) and self._zone_side(x, y):
                # Lettering was identified from a measured zone-side vantage.
                # Pixel area under oblique viewing does not establish a back
                # view. Keep this position and let the following camera/lidar
                # alignment measure the board face before any gate movement.
                self.target = (x, y, th)
                self.headings = [th]
                self._high = False
                self.phase = 'approach'
                self.router.reset()
                self.mav.log('FindReturnBanner: retaining measured camera vantage '
                    'for lidar alignment; area-derived stand-off is outside the zone side')
                return py_trees.common.Status.RUNNING
        return super()._found(bx, by, th, rng)
