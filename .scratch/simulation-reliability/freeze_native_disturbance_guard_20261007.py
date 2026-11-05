"""Freeze current sources and isolate the rejected-for-gust admission diagnostic."""
from pathlib import Path
import ast,hashlib,json,os,shutil,textwrap
root=Path(__file__).resolve().parents[2]
out=root/'.scratch/native_disturbance_guard_candidate_20261007'
out.mkdir(exist_ok=True)
assert not (out/"diagnostic_source_manifest.json").exists(), "Preserve existing frozen evidence"
manifest={}
for directory in ('src','scripts','sim'):
 for path,dirs,files in os.walk(root/directory):
  dirs[:]=[d for d in dirs if d not in ('__pycache__','node_modules','.git','build','dist')]
  for name in files:
   p=Path(path)/name;relative=p.relative_to(root)
   destination=out/relative;destination.parent.mkdir(parents=True,exist_ok=True)
   shutil.copy2(p,destination) if not destination.exists() else None
   assert destination.read_bytes()==p.read_bytes(), relative
   manifest[str(relative).replace('\\','/')]=hashlib.sha256(p.read_bytes()).hexdigest()
controller=out/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
source=controller.read_text(encoding="utf-8");tree=ast.parse(source)
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='VelocityController')
method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_publish')
lines=source.splitlines(keepends=True)
before=''.join(lines[method.lineno-1:method.end_lineno]);body=textwrap.dedent(before)
a=body.index('        def motion_clear(command):');b=body.index('        if not motion_clear((vx,vy)):',a)
block=body[a:b].replace('def motion_clear(command):','def disturbance_motion_clear(command, wind, wind_rate):',1)
wrapper='''        def motion_clear(command):
            # A response mismatch may masquerade as helpful disturbance.
            # Diagnostic only: require the zero-disturbance prediction too.
            return (disturbance_motion_clear(command, wind, wind_rate)
                    and disturbance_motion_clear(command, np.zeros(2), np.zeros(2)))
'''
body=body[:a]+block+wrapper+body[b:]
after=textwrap.indent(body,'    ')
lines[method.lineno-1:method.end_lineno]=[after+'\n']
new=''.join(lines);compile(new,str(controller),'exec');controller.write_bytes(new.encode())
manifest[str(controller.relative_to(out)).replace('\\','/')]=hashlib.sha256(controller.read_bytes()).hexdigest()
(out/'diagnostic_source_manifest.json').write_text(json.dumps(manifest,indent=2))
(out/'diagnostic_provenance.json').write_text(json.dumps(dict(scope='Native focused return diagnostic only; coupled gust cases already fail; not production adoption',baseline_controller_sha256=hashlib.sha256((root/controller.relative_to(out)).read_bytes()).hexdigest(),candidate_controller_sha256=hashlib.sha256(controller.read_bytes()).hexdigest(),files=len(manifest)),indent=2))
print(out)
