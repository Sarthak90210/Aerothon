from pathlib import Path
p=Path('sim/test_frame_conventions.py');s=p.read_text()
s=s.replace('sp = self.tick_with(make_scan(left_m=3.0, right_m=0.5, front_m=10.0))','self.node._planner.observe(*self.node.conditioned(make_scan(3.0,1.0,10.0)))\n        self.node._publish(.2,.2,10.0,.5,{})\n        sp = self.sent[-1]')
s=s.replace('sp = self.tick_with(make_scan(left_m=0.5, right_m=3.0, front_m=10.0))','self.node._planner.observe(*self.node.conditioned(make_scan(1.0,3.0,10.0)))\n        self.node._publish(.2,-.2,10.0,-.5,{})\n        sp = self.sent[-1]')
p.write_text(s)
p=Path('src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py');s=p.read_text()
a=s.index('    def _escape(');b=s.index('    def _strips(',a);s=s[:a]+s[b:]
a=s.index('"""Corridor navigation');b=s.index('\nimport json',a)
s=s[:a]+'''"""Corridor navigation over connected lidar-observed free space.

All paths and recovery velocities enforce 0.70 m centre-to-surface clearance.
Unobserved reverse paths, stale poses/scans and exhausted recovery stop.
MAVROS body velocities use FLU: +x forward, +y left, +z up.
No venue geometry or simulator truth is consumed here.
"""
'''+s[b:]
s=s.replace('yaw_rate = float(self._yaw_rate_for(bearing))','yaw_rate = float(self._yaw_rate_for(bearing)) if abs(vx)+abs(vy)>1e-6 else 0.0')
p.write_text(s)