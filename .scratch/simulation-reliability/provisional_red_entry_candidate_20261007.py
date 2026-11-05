"""Camera-only early obstacle evidence, distinct from persistent red confirmation."""
import inspect
import json
import math
import textwrap
from partial_red_boundary_candidate_20261007 import partial_boundaries


def install(red_class, commander_class, evidence):
    evidence.mkdir(exist_ok=False)
    original = textwrap.dedent(inspect.getsource(red_class.on_image))
    candidate = original
    old = '    cnts, frac = [], 0.0'
    assert candidate.count(old) == 1
    candidate = candidate.replace(old, old+'''
    provisional = []
    if ok:
        provisional = partial_boundaries(normalise(frame), pose[2], self._hfov,
            lambda contour, wh: self.project_polygon(contour, wh, pose))''')
    old = 'detail["status"] = RED if cnts else CLEAR'
    assert candidate.count(old) == 1
    candidate = candidate.replace(old, 'detail["status"] = RED if cnts or provisional else CLEAR')
    old = '    detail["confirmed_area_m2"] = round(self.grid.area_m2(), 1)'
    assert candidate.count(old) == 1
    candidate = candidate.replace(old, old+'''
    detail["provisional_exclusions"] = [list(bbox(item['polygon'])) for item in provisional]
    detail["provisional_basis"] = 'clipped solid red and connected visible white backing'
    detail["provisional_confirmed"] = False''')
    candidate = candidate.replace('Bool(data=bool(cnts))', 'Bool(data=bool(cnts) or bool(provisional))')
    (evidence/'original_on_image.py').write_text(original)
    (evidence/'candidate_on_image.py').write_text(candidate)
    namespace = dict(red_class.on_image.__globals__, partial_boundaries=partial_boundaries)
    exec(compile(candidate, str(evidence/'candidate_on_image.py'), 'exec'), namespace)
    red_class.on_image = namespace['on_image']

    original = textwrap.dedent(inspect.getsource(commander_class._on_redzone))
    old = '    self.exclusions = [tuple(float(v) for v in r) for r in ex if len(r) == 4]'
    assert original.count(old) == 1
    candidate = original.replace(old, '''    confirmed = [tuple(float(v) for v in r) for r in ex if len(r) == 4]
    provisional = []
    now = self.node.get_clock().now().nanoseconds * 1e-9
    try:
        capture = float(d['capture_stamp'])
        if math.isfinite(capture) and 0 <= now-capture <= .5 and self.redzone_status in ('CLEAR','RED'):
            for rectangle in d.get('provisional_exclusions', []):
                if len(rectangle) != 4:
                    continue
                values = tuple(float(v) for v in rectangle)
                if all(math.isfinite(v) for v in values) and values[0] < values[1] and values[2] < values[3]:
                    provisional.append(values)
    except (KeyError, TypeError, ValueError):
        provisional = []
    self.provisional_exclusions = provisional
    self.confirmed_exclusions = confirmed
    self.exclusions = confirmed + provisional''')
    (evidence/'original_on_redzone.py').write_text(original)
    (evidence/'candidate_on_redzone.py').write_text(candidate)
    namespace = dict(commander_class._on_redzone.__globals__)
    exec(compile(candidate, str(evidence/'candidate_on_redzone.py'), 'exec'), namespace)
    commander_class._on_redzone = namespace['_on_redzone']
