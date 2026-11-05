"""Single-variable altitude replay controls; no production edits."""
import importlib.util,json,sys
from pathlib import Path
from unittest.mock import patch
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from avoidance.velocity_controller import VelocityController
path=root/'.scratch/simulation-reliability/test_v35_return_altitude_seam_20261008.py'
spec=importlib.util.spec_from_file_location('altitude_probe',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original_loads=json.loads;original_velocity=VelocityController._on_velocity
def fixed_errors(s,*args,**kwargs):
 data=original_loads(s,*args,**kwargs)
 if isinstance(data,dict) and data.get('scope','').startswith('Evaluation-only recorded barometer'):
  data['errors']=[[r[0],data['errors'][0][1]] for r in data['errors']]
 return data
def tracked(self,message):
 original_velocity(self,message)
 sample=(self._fcu_velocity_t,float(message.twist.linear.z))
 previous=getattr(self,'_probe_previous',None)
 if self.enabled and previous is not None and sample[0]>previous[0]:
  self._probe_d=getattr(self,'_probe_d',0.)+.5*(sample[0]-previous[0])*(sample[1]+previous[1])
 self._probe_previous=sample
def relative(self):
 if not hasattr(self,'_probe_base'):self._probe_base=self._alt
 error=self._hold_alt-self._probe_base-getattr(self,'_probe_d',0.)
 return max(-.6,min(.6,.8*error))
original_correction=VelocityController._alt_correction
def half_gain(self):return .5*original_correction(self)
results=[]
for label,patchers in [('unchanged',[]),('constant barometer error',[patch.object(m.json,'loads',fixed_errors)]),('half vertical gain',[patch.object(VelocityController,'_alt_correction',half_gain)]),('measured vertical displacement',[patch.object(VelocityController,'_on_velocity',tracked),patch.object(VelocityController,'_alt_correction',relative)])]:
 from contextlib import ExitStack
 try:
  with ExitStack() as stack:
   for p in patchers:stack.enter_context(p)
   m.test_return_corridor_remains_above_ground_through_recorded_baro_wander()
  verdict='PASS'
 except AssertionError:verdict='FAIL'
 results.append(dict(control=label,verdict=verdict))
print(json.dumps(results,indent=2));(root/'logs/reliability_v35_altitude_causes_20261008.json').write_text(json.dumps(results,indent=2))
