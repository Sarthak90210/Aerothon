"""Camera-only handoff candidate retaining an oblique but proven observer pose."""
import math
import py_trees
from mission_bt.mission_tree import FindReturnBanner

class ObliqueObserverReturnBanner(FindReturnBanner):
    def _found(self, bx, by, th, rng):
        x,y=self.mav.pos()[:2]
        normal=self._inward_normal(bx,by)
        if normal is not None and self._zone_side(x,y):
            face_heading=math.atan2(-normal[1],-normal[0])
            off_normal=abs(self._wrap(th-face_heading))
            if off_normal>math.radians(45):
                # An oblique pixel area is not a measured board position.
                # Preserve the viewpoint where lettering was admitted; the
                # following alignment leaf measures face/range with lidar.
                self.target=(x,y,th);self.headings=[th]
                self._high=False;self.phase='approach';self.router.reset()
                self.mav.log('FindReturnBanner: retaining identified observer viewpoint; '
                    f'area-derived ray is {math.degrees(off_normal):.1f} deg off inferred face normal')
                return py_trees.common.Status.RUNNING
        return super()._found(bx,by,th,rng)
