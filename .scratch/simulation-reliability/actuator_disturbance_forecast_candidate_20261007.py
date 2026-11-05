"""Isolated forecast correction; no simulator state enters this calculation."""
import inspect
import textwrap


def install(controller, evidence):
    original=controller._publish
    before=textwrap.dedent(inspect.getsource(original))
    after=before
    replacements={
        'velocity = ground.copy()':'actuator = ground-wind\n        velocity = ground.copy()',
        'goal = rotation @ self._effective_command(sample_epoch+t)+wind+t*wind_rate':
            'goal = rotation @ self._effective_command(sample_epoch+t)',
        'goal = ground.copy()':'goal = ground-wind',
        'goal = turning+wind+t*wind_rate':'goal = turning',
        'goal = np.zeros(2)':'goal = -(wind+(packet_wait+tau)*wind_rate)',
        'change = (goal-velocity)*min(1.0,dt/tau)':
            'change = (goal-actuator)*min(1.0,dt/tau)',
        'velocity += change':
            'actuator += change\n            velocity = actuator+wind+min(t+dt,packet_wait+tau)*wind_rate',
    }
    for old,new in replacements.items():
        assert after.count(old)==1,old
        line=next(line for line in after.splitlines() if old in line)
        indent=line[:len(line)-len(line.lstrip())]
        # Replacement continuations use the same block indentation.
        lines=new.splitlines()
        adjusted='\n'.join([lines[0]]+[indent+line.lstrip() for line in lines[1:]])
        after=after.replace(old,adjusted)
    evidence.mkdir(exist_ok=False)
    (evidence/'original_publish.py').write_text(before)
    (evidence/'candidate_publish.py').write_text(after)
    namespace=dict(original.__globals__)
    exec(compile(after,str(evidence/'candidate_publish.py'),'exec'),namespace)
    controller._publish=namespace['_publish']


def check_constant_command_ramping_disturbance():
    # This algebra fixture checks the model, not a measured aircraft signal.
    tau,dt,rate=.6,.05,.2
    raw=.3
    actuator=0.
    separate=0.
    previous=0.
    for step in range(20):
        t=step*dt
        actuator+=(raw-actuator)*dt/tau
        expected=actuator+(t+dt)*rate
        separate+=(raw-separate)*dt/tau
        corrected=separate+(t+dt)*rate
        previous+=(raw+t*rate-previous)*dt/tau
        assert abs(corrected-expected)<1e-12
    return dict(corrected_ground_velocity=corrected,
                original_ground_velocity=previous,
                original_error=abs(previous-expected),
                scope='Controlled model algebra; no flight qualification')
