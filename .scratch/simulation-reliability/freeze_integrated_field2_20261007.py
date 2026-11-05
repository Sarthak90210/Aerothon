"""Freeze current integrated code before repeating field seed 2."""
import hashlib,json,os,shutil,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'.scratch/integrated_field2_candidate_20261007';out.mkdir(exist_ok=False)
evidence=root/'logs/reliability_integrated_field2_source_20261007';evidence.mkdir(exist_ok=False)
suffixes={'.py','.sh','.cpp','.hpp','.h','.xml','.yaml','.yml','.json','.sdf','.xacro','.toml','.ts','.tsx','.rs','.parm','.cfg','.ini'}
manifest={}
for directory in ('src','scripts','sim'):
 for path,dirs,files in os.walk(root/directory):
  dirs[:]=[d for d in dirs if d not in ('node_modules','__pycache__','.git','build','dist')]
  for name in files:
   p=Path(path)/name
   if p.suffix not in suffixes:continue
   relative=p.relative_to(root);target=out/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
   manifest[str(relative).replace('\\','/')]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
with zipfile.ZipFile(evidence/'frozen_source.zip','x',zipfile.ZIP_DEFLATED) as z:
 for name in manifest:z.write(out/name,name)
 z.write(out/'source_manifest.json','source_manifest.json')
review=dict(scope='Current integrated normal navigation startup, object-level field seed 2; rendered/motor delivery qualification omitted',files=len(manifest),archive_sha256=hashlib.sha256((evidence/'frozen_source.zip').read_bytes()).hexdigest(),accepted_source=False)
(evidence/'provenance.json').write_text(json.dumps(review,indent=2));print(json.dumps(review))
