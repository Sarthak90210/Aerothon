"""One-variable prototype: retain the tolerance around a fresh settle window."""
import inspect,json,sys,textwrap
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'.scratch/simulation-reliability'))
import test_recorded_gate_physics_seam_20261008 as seam
import mission_bt.gate_braking as module
body=textwrap.dedent(inspect.getsource(module.BrakedGateAdvance.update))
body=body.replace("if self._phase == 'BRAKE':\n        self._brake_position()", "if self._phase == 'BRAKE':\n        self._brake_position()\n        if self._settle_first is None:\n            self._settle_position = self.mav.pos()")
assert body.count('math.dist(self.mav.pos(),self._brake_hold)')==2
body=body.replace('math.dist(self.mav.pos(),self._brake_hold)','math.dist(self.mav.pos(),self._settle_position)')
body=body.replace('super().update()', 'GateAdvance.update(self)')
namespace=dict(module.__dict__);exec(body,namespace);module.BrakedGateAdvance.update=namespace['update']
result=seam.replay();result['probe']='Fresh measured position at start of settle window; same speed .08, position .25, three distinct captures and .3 s span; original held command retained'
(root/'logs/reliability_gate_settle_window_probe_20261008.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
assert result['status']=='Status.SUCCESS'
assert not result['contacts'] and result['minimum_clearance_m']>=.70
