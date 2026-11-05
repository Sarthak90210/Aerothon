"""Batch identical clearance samples to reduce certificate computation time."""
import inspect
import math
import textwrap
import numpy as np


def sample_segment(start,end):
    return np.linspace(start,end,max(2,int(math.dist(start,end)/.05)+2))


def polyline_clear(planner,segments):
    points=np.concatenate(segments) if segments else np.zeros((1,2))
    return bool(planner.known(points).all() and
                (planner.distances(points)>=planner.clearance+.025).all())


def install(controller,evidence):
    original=controller._publish
    source=textwrap.dedent(inspect.getsource(original))
    candidate=source
    old='            point = np.zeros(2)'
    # inspect.dedent leaves method-local indentation; find exact line.
    line=next(line for line in candidate.splitlines() if line.strip()=='point = np.zeros(2)')
    indent=line[:len(line)-len(line.lstrip())]
    candidate=candidate.replace(line,line+'\n'+indent+'segments = []')
    old=next(line for line in candidate.splitlines() if 'if not self._planner.segment_clear(point,nxt):' in line)
    indent=old[:len(old)-len(old.lstrip())]
    block=old+'\n'+indent+'    return False'
    assert candidate.count(block)==1
    candidate=candidate.replace(block,indent+'segments.append(sample_segment(point,nxt))')
    old=indent[:-4]+'return True'
    assert candidate.count(old)==1
    candidate=candidate.replace(old,indent[:-4]+'return polyline_clear(self._planner,segments)')
    evidence.mkdir(exist_ok=False)
    (evidence/'original_publish.py').write_text(source)
    (evidence/'candidate_publish.py').write_text(candidate)
    namespace=dict(original.__globals__,sample_segment=sample_segment,polyline_clear=polyline_clear)
    exec(compile(candidate,str(evidence/'candidate_publish.py'),'exec'),namespace)
    controller._publish=namespace['_publish']
