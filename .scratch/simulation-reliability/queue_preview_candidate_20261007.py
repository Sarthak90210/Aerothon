"""Isolated preview of changing measured disturbance across command transport."""
import inspect,textwrap

def install(controller,evidence):
    original=controller._compensated
    before=textwrap.dedent(inspect.getsource(original))
    needle="prediction = float(self._g('vel_response_s'))"
    assert before.count(needle)==1
    after=before.replace(needle,"prediction = float(self._g('vel_response_s')) + float(self._g('vel_command_delay_s'))")
    evidence.mkdir(exist_ok=False)
    (evidence/'original_compensated.py').write_text(before)
    (evidence/'candidate_compensated.py').write_text(after)
    namespace=dict(original.__globals__)
    exec(compile(after,str(evidence/'candidate_compensated.py'),'exec'),namespace)
    controller._compensated=namespace['_compensated']
