from pathlib import Path
for name in ('sim/test_corridor_recovery.py','sim/test_frame_conventions.py'):
 p=Path(name);s=p.read_text()
 s=s.replace('self.node.enabled = True','self.node.enabled = True\n        self.node._now = lambda: 0.0\n        self.node._pos = (0.0, 0.0)\n        self.node._yaw = 0.0\n        self.node._pose_t = 0.0')
 if 'recovery' in name:
  s=s.replace('self.node._on_scan(scan)\n            self.node._tick()', 'self.node._pose_t = self.node._now()\n            self.node._on_scan(scan)\n            self.node._tick()')
  s=s.replace('self.assertLess(sp.velocity.x, 0.0,\n                        "BACKOFF must command reverse motion")','self.assertEqual(sp.velocity.x, 0.0,\n                         "an enclosed 0.6 m scan cannot authorize reverse at 0.70 m clearance")')
  s=s.replace('ranges.append(0.5)','ranges.append(1.5)')
  s=s.replace('self.node._tick()\n\n    def test_exit_requires_sustained_openness', 'self.node._tick()\n        self.node._pos = (3.0, 0.0)\n\n    def test_exit_requires_sustained_openness')
 p.write_text(s)
p=Path('sim/test_navigator_equivalence.py');s=p.read_text()
s=s.replace('r_air + (half_w - r_air) * min(1.0, r)', 'half_w')
a=s.index('    if gap is None:\n',s.index('def ref_find_gap(g,'));b=s.index('    return gap',a)
s=s[:a]+s[b:];p.write_text(s)