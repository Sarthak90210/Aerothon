"""One-variable controls through actual gate, guard and normal airframe."""
import importlib.util,json,sys
from pathlib import Path
from unittest.mock import patch
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from mission_bt.gate_braking import BrakedGateAdvance
from mission_bt.mav_commander import Mav
path=root/'.scratch/simulation-reliability/test_v34_brake_physics_seam_20261008.py'
spec=importlib.util.spec_from_file_location('brake_probe',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
original=json.loads;results=[]
def execute(label,patcher):
 try:
  with patcher:module.test_recorded_gate_entry_finishes_without_contact_or_clearance_loss()
  verdict='PASS'
 except AssertionError as e:verdict='FAIL'
 trace=json.loads((root/'.scratch/simulation-reliability/brake_v34_replay_trace_20261008.json').read_text())
 results.append(dict(control=label,verdict=verdict,final=trace[-1],ticks=len(trace)))
def relative(self):
 previous=getattr(self,'_probe_previous',None);d=getattr(self,'_probe_displacement',[0.,0.])
 for s in getattr(self.mav,'ground_velocity_samples',()):
  if previous is not None and s[0]<=previous[0]:continue
  if previous is not None:
   dt=s[0]-previous[0];d[0]+=.5*dt*(s[1]+previous[1]);d[1]+=.5*dt*(s[2]+previous[2])
  previous=s
 self._probe_previous=previous;self._probe_displacement=d
 x,y,_=self.mav.pos();self._brake_hold=(x-d[0],y-d[1],self._flight_alt)
 self.mav.goto(*self._brake_hold,self._brake_yaw)
def damping(self):
 x,y,z=self._brake_hold;s=self.mav.ground_velocity_samples[-1]
 self.mav.goto(x-s[1],y-s[2],z,self._brake_yaw)
def fixed_errors(s,*args,**kwargs):
 data=original(s,*args,**kwargs)
 if isinstance(data,dict) and data.get('scope','').startswith('Evaluation only'):
  initial=data['errors'][0][1:]
  data['errors']=[[r[0],*initial] for r in data['errors']]
 return data
execute('unchanged',patch.object(Mav,'keepout_m',1.,create=True))
execute('fixed estimator errors',patch.object(module.json,'loads',fixed_errors))
execute('velocity damping gain 1s',patch.object(BrakedGateAdvance,'_brake_position',damping))
execute('relative ground motion anchor',patch.object(BrakedGateAdvance,'_brake_position',relative))
(root/'logs/reliability_v34_gate_brake_causes_20261008.json').write_text(json.dumps(results,indent=2))
print(json.dumps([dict(control=r['control'],verdict=r['verdict'],ticks=r['ticks']) for r in results],indent=2))
