import hashlib
import json
from pathlib import Path
import zipfile

bundle = Path('/home/pi5/aerothon-deploy/runtime_20261013.zip')
root = Path('/home/pi5/aerothon_ws')
assert not root.exists(), 'Use a fresh workspace'
assert hashlib.sha256(bundle.read_bytes()).hexdigest() == '4786afd9c4bbb06671e9cdc75e5634b8765beb177b19db795e2f8ebfe117f4f3'
with zipfile.ZipFile(bundle) as archive:
    assert archive.testzip() is None
    manifest = json.loads(archive.read('runtime_manifest.json'))
    assert set(archive.namelist()) == set(manifest['files']) | {'runtime_manifest.json'}
    for name, digest in manifest['files'].items():
        target = (root / name).resolve()
        assert target.is_relative_to(root)
        assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name
    archive.extractall(root)
    for entry in archive.infolist():
        if entry.filename.endswith('.sh'):
            (root / entry.filename).chmod(0o755)
print(json.dumps({'verified_files': len(manifest['files']), 'workspace': str(root)}))
