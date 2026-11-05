"""Run the standalone candidate leaf in the preserved component fixture."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = (HERE / 'probe_gate_advance_early_speed_20261007.py').read_text()
source = source.replace("choices=('baseline', 'arrival_only', 'early_speed')", "choices=('braked_candidate',)")
source = source.replace('from mission_bt.mission_tree import GateAdvance',
    'from gate_advance_braking_candidate_20261007 import BrakedGateAdvance as GateAdvance')
source = source.replace('from geometry_msgs.msg import PoseStamped',
    'from geometry_msgs.msg import PoseStamped, TwistStamped')
source = source.replace('class Mav:\n',
    'class Mav:\n    _delivery_velocity = MavCommander._delivery_velocity\n')
source = source.replace("        self.pending_speed=[]", "        self.speed_cmd=world.speed_cap\n        self.delivery_inputs={}\n        self.pending_speed=[]")
source = source.replace('        self.pending_speed.append((world.t+.4,request,future))',
    '        self.speed_cmd=float(value)\n        self.pending_speed.append((world.t+.4,request,future))')
source = source.replace('        self._on_scan(s)\n',
    "        self._on_scan(s)\n        self.delivery_inputs.update(pose_stamp=world.t)\n        velocity=TwistStamped();velocity.header=s.header\n        velocity.twist.linear.x=float(world.ground_velocity[0])\n        velocity.twist.linear.y=float(world.ground_velocity[1])\n        velocity.twist.linear.z=float(world.ground_velocity[2])\n        self._delivery_velocity(velocity)\n")
source = source.replace('leaf=GateAdvance(mav, advance_m=4.45,',
    'leaf=GateAdvance(mav, gate_speed_mps=a.cap, advance_m=4.45,')
start = source.index('admission_future=None\n')
end = source.index('rows=[];', start)
source = source[:start] + source[end:]
source = source.replace("    early_cap_mps=a.cap,speed_acks=mav.speed_acks,", "    early_cap_mps=a.cap,speed_acks=mav.speed_acks,\n    candidate_source_sha256=hashlib.sha256(Path(__file__).with_name('gate_advance_braking_candidate_20261007.py').read_bytes()).hexdigest(),")
target = HERE / 'probe_braked_gate_component_20261007.py'
with target.open('x') as output:
    output.write(source)
print(target)
