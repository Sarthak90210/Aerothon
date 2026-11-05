"""Integrate bounded camera retries and the native split admission repair."""
import ast,hashlib,textwrap
from pathlib import Path
root=Path(__file__).resolve().parents[2]
path=root/'src/aerothon_mission/mission_bt/mission_bt/mission_tree.py'
source=path.read_text(encoding='utf-8');lines=source.splitlines(keepends=True);tree=ast.parse(source)
edits=[]
for candidate,original,methods in [('fine_return_framing','AlignToBanner',('_reset_recovery','_give_up')),('clipped_bearing_return','FindReturnBanner',('initialise','update'))]:
    prototype=ast.parse((root/f'.scratch/simulation-reliability/{candidate}_candidate_20261007.py').read_text(encoding='utf-8'))
    subclass=next(n for n in prototype.body if isinstance(n,ast.ClassDef))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==original)
    for name in methods:
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name)
        extra=next(n for n in subclass.body if isinstance(n,ast.FunctionDef) and n.name==name)
        # Remove the explicit super call: these statements now execute inside
        # the real startup leaf before/after its existing implementation.
        statements=[n for n in extra.body if 'super().' not in ast.unparse(n)]
        body=textwrap.indent('\n'.join(ast.unparse(n) for n in statements)+'\n','        ')
        if name in ('initialise','_reset_recovery'):
            edits.append((method.end_lineno,method.end_lineno,body))
        else:edits.append((method.body[0].lineno-1,method.body[0].lineno-1,body))
for start,end,body in sorted(edits,reverse=True):lines[start:end]=[body]
new=''.join(lines);compile(new,str(path),'exec');path.write_bytes(new.encode())
controller=root/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
source=controller.read_text(encoding='utf-8')
assert source.count('            def motion_clear(command):')==1
source=source.replace('            def motion_clear(command):','            def disturbance_motion_clear(command, wind, wind_rate):',1)
needle='            if not motion_clear((vx,vy)):';assert source.count(needle)==1
source=source.replace(needle,'''            def motion_clear(command):
                # A response mismatch may masquerade as helpful disturbance.
                # Require clearance for the zero-disturbance prediction too.
                return (disturbance_motion_clear(command, wind, wind_rate)
                        and disturbance_motion_clear(command, np.zeros(2), np.zeros(2)))
'''+needle)
compile(source,str(controller),'exec');controller.write_bytes(source.encode())
for p in (path,controller):print(p.relative_to(root),hashlib.sha256(p.read_bytes()).hexdigest())
