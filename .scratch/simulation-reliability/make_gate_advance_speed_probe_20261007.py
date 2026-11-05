"""Prepare a scratch GateAdvance speed-admission experiment from the baseline."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
original = (HERE / 'probe_gate_advance_admission_20261007.py').read_text()
candidate = original.replace("choices=('baseline', 'arrival_only')", "choices=('baseline', 'arrival_only', 'early_speed')")
candidate = candidate.replace("a = p.parse_args()", "p.add_argument('--cap', type=float, default=.35)\na = p.parse_args()\nassert .05 <= a.cap <= 5.")
candidate = candidate.replace("    def __init__(self):\n", "    def __init__(self):\n        self.pending_speed=[]\n        self.speed_acks=[]\n")
needle = '    def observe(self):\n'
replacement = '''    def set_speed(self, value):
        from mavros_msgs.srv import CommandLong
        future=SimpleNamespace(done=lambda:False,result=lambda:None)
        request=CommandLong.Request();request.command=178
        request.param1=1.;request.param2=float(value);request.param3=-1.
        self.pending_speed.append((world.t+.4,request,future))
        return future
    def process_speed(self):
        while self.pending_speed and self.pending_speed[0][0]<=world.t+1e-9:
            due,request,future=self.pending_speed.pop(0)
            response=world._srv_command(request,SimpleNamespace(success=False,result=0))
            future.done=lambda:True
            future.result=lambda response=response:response
            self.speed_acks.append(dict(stamp=world.t,requested_cap=request.param2,
                success=response.success))
    def observe(self):
'''
assert candidate.count(needle) == 1
candidate = candidate.replace(needle, replacement)
needle = 'leaf.initialise()\n'
replacement = '''leaf.initialise()
admission_future=None
admission_hold=None
original_update=leaf.update
def guarded_update():
    global admission_future,admission_hold
    if a.mode!='early_speed':return original_update()
    if admission_hold is None:admission_hold=mav.pos()
    # Hold the measured approach position until the actual command service
    # has acknowledged the cap. Do not advance on a merely transmitted request.
    if admission_future is None:admission_future=mav.set_speed(a.cap)
    if not admission_future.done():
        mav.goto(*admission_hold,mav.yaw())
        return py_trees.common.Status.RUNNING
    if not admission_future.result().success:
        mav.goto(*admission_hold,mav.yaw())
        return py_trees.common.Status.FAILURE
    return original_update()
leaf.update=guarded_update
'''
assert candidate.count(needle) == 1
candidate = candidate.replace(needle, replacement)
candidate = candidate.replace('    if step%10==0:\n        mav.observe()', '    mav.process_speed()\n    if step%10==0:\n        mav.observe()')
candidate = candidate.replace("if a.mode=='arrival_only' and speed>.08:", "if a.mode in ('arrival_only','early_speed') and speed>.08:")
candidate = candidate.replace("    declared_advance_m=4.45,actual_latched_target=leaf._target,", "    declared_advance_m=4.45,actual_latched_target=leaf._target,\n    early_cap_mps=a.cap,speed_acks=mav.speed_acks,\n    speed_service_delay_assumption_s=.4,arrival_speed_limit_mps=.08,")
target = HERE / 'probe_gate_advance_early_speed_20261007.py'
with target.open('x') as output:
    output.write(candidate)
print(target)
