from pathlib import Path
import hashlib,json,shutil,zipfile

root=Path('/home/pi5/aerothon_ws').resolve()
archive=Path('/home/pi5/aerothon-deploy/remote-runtime.zip')
with zipfile.ZipFile(archive) as z:
 manifest=json.loads(z.read('runtime_manifest.json'))
 for name,digest in manifest['files'].items():
  target=(root/name).resolve()
  if not target.is_relative_to(root):raise RuntimeError('unsafe bundle path')
  if hashlib.sha256(z.read(name)).hexdigest()!=digest:raise RuntimeError('bad bundle hash')
 old=json.loads((root/'runtime_manifest.json').read_text())
 before={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in old['files'] if (root/name).is_file()}
 receipt=Path('/home/pi5/aerothon-deploy/before-remote-runtime.json')
 if receipt.exists():raise RuntimeError('evidence path already exists')
 receipt.write_text(json.dumps({'source':before,'manifest':old,'bundle':hashlib.sha256(archive.read_bytes()).hexdigest()},indent=2))
 for name in old['files']:
  if name not in manifest['files']:
   target=(root/name).resolve()
   if not target.is_relative_to(root):raise RuntimeError('unsafe obsolete path')
   target.unlink(missing_ok=True)
 for name in [*manifest['files'],'runtime_manifest.json']:
  target=root/name
  target.parent.mkdir(parents=True,exist_ok=True)
  target.write_bytes(z.read(name))
 for name,digest in manifest['files'].items():
  assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
 print(json.dumps({'verified_files':len(manifest['files']),'local_packages':manifest['local_ros_packages'],'source_changed':sum(before.get(n)!=h for n,h in manifest['files'].items())}))
