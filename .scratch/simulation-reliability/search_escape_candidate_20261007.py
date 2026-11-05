"""Isolated router repair. Keep a running rendered recording source-frozen."""
import inspect
import textwrap
from mission_bt.search_planner import routing_obstacles

def install(cls):
    original = cls._carrot
    def escape_first(self, mav, wx, wy):
        px, py = mav.pos()[:2]
        if any(x0 <= px <= x1 and y0 <= py <= y1
               for x0,x1,y0,y1 in routing_obstacles(self._exclusions(mav), self.clearance_m)):
            return wx, wy
        return original(self, mav, wx, wy)
    cls._carrot = escape_first
    source = textwrap.dedent(inspect.getsource(cls._segment_safe))
    old = 'for x0,x1,y0,y1 in containing:'
    assert source.count(old) == 1
    source = source.replace(old, 'for x0,x1,y0,y1 in containing[:1]:')
    scope = dict(cls._segment_safe.__globals__)
    exec(compile(source, '<sequential observed exclusion escape>', 'exec'), scope)
    cls._segment_safe = scope['_segment_safe']
