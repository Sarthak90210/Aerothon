from pathlib import Path
import zipfile,json,hashlib,sys
root=Path('/home/pi5/aerothon_ws').resolve()
with zipfile.ZipFile(sys.argv[1]) as z:
 m=json.loads(z.read('runtime_manifest.json'))
 previous=json.loads((root/'runtime_manifest.json').read_text())
 for n,h in m['files'].items():
  assert (root/n).resolve().is_relative_to(root)
  assert hashlib.sha256(z.read(n)).hexdigest()==h
 for n,h in m['files'].items():
  p=root/n
  if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=h:
   p.parent.mkdir(parents=True,exist_ok=True)
   p.write_bytes(z.read(n))
 for n in previous['files']:
  if n not in m['files']:
   p=(root/n).resolve()
   assert p.is_relative_to(root)
   p.unlink(missing_ok=True)
 (root/'runtime_manifest.json').write_bytes(z.read('runtime_manifest.json'))
 assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in m['files'].items())
 print(json.dumps({'verified_files':len(m['files']),'bundle_sha256':hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()}))
