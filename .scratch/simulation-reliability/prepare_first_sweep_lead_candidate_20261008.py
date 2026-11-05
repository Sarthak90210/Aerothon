"""Retain the first complete sweep; promote its stable observed lead afterwards."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
path=root/'src/aerothon_mission/mission_bt/mission_bt/mission_tree.py'
text=path.read_text(encoding='utf-8')
rejected=(root/'.scratch/reduced_scope_v21_candidate_20261008'/path.relative_to(root)).read_text(encoding='utf-8')
start=rejected.index('    def _orbit_stable_green(')
end=rejected.index('    @staticmethod\n    def _wrap',start)
method=rejected[start:end].replace('_orbit_stable_green','_remember_stable_green')
method=method.replace('"""Use a repeated whole-board lead for guarded observation only."""',
                      '"""Remember a repeated whole-region lead; complete the initial sweep."""')
method=method.replace('if self._early_green_orbit_used or self._orbit is not None:',
                      'if self._orbit is not None or self._second_look_done:')
method=method.replace('        self._green = fix\n        self._early_green_orbit_used = True\n        return self._next_orbit_vantage()',
    '        if better_green(fix, self._first_sweep_lead):\n            self._first_sweep_lead = dict(fix)\n        return False')
needle='        self._last_banner_sample = None\n\n    @staticmethod\n    def _wrap'
replacement='''        self._last_banner_sample = None
        self._green_lead = None
        self._green_lead_samples = 0
        self._green_lead_stamp = None
        self._green_lead_first = None

'''+method+'    @staticmethod\n    def _wrap'
assert needle in text;text=text.replace(needle,replacement,1)
needle='        self._green = None           # best green_fix, not the outbound gate'
assert needle in text;text=text.replace(needle,needle+'\n        self._first_sweep_lead = None',1)
needle='''        if self.phase == "sweep":
            if self.hi >= len(self.headings) and not self._second_look_done:
'''
replacement='''        if self.phase == "sweep":
            if (self.hi >= len(self.headings) and not self._second_look_done
                    and self._orbit is None and self._first_sweep_lead is not None):
                # Keep every initial view. A stable whole-region lead already
                # observed during this sweep supplies guarded orbit geometry,
                # not identity or permission to enter the gate.
                self._green = self._first_sweep_lead
                if self._next_orbit_vantage():
                    return py_trees.common.Status.RUNNING
            if self.hi >= len(self.headings) and not self._second_look_done:
'''
assert needle in text;text=text.replace(needle,replacement,1)
needle='''                if f is not None and better_green(f, self._green):
                    self._green = f
'''
assert text.count(needle)==1
text=text.replace(needle,needle+'                self._remember_stable_green(f, observation if callable(observe) else None, now)\n',1)
path.write_text(text,encoding='utf-8',newline='\n')
print('First complete sweep retained; stable observed lead tried before repeated sweep')
