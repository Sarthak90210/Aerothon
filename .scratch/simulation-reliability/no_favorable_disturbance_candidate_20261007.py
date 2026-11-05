"""Diagnostic admission guard: inferred disturbance may not justify a zero-wind collision."""
import inspect,textwrap

def install(controller,evidence):
    original=controller._publish
    before=textwrap.dedent(inspect.getsource(original))
    start=before.index('        def motion_clear(command):')
    end=before.index('        if not motion_clear((vx,vy)):',start)
    block=before[start:end].replace('def motion_clear(command):','def disturbance_motion_clear(command, wind, wind_rate):',1)
    wrapper='''        def motion_clear(command):
            # A latency or actuator mismatch can masquerade as helpful wind.
            # Require safety without the inferred cancellation too.
            return (disturbance_motion_clear(command, wind, wind_rate)
                    and disturbance_motion_clear(command, np.zeros(2), np.zeros(2)))
'''
    after=before[:start]+block+wrapper+before[end:]
    evidence.mkdir(exist_ok=False)
    (evidence/'original_publish.py').write_text(before)
    (evidence/'candidate_publish.py').write_text(after)
    namespace=dict(original.__globals__)
    exec(compile(after,str(evidence/'candidate_publish.py'),'exec'),namespace)
    controller._publish=namespace['_publish']
