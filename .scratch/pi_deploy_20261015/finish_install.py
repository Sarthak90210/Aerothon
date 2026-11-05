"""Finish the interrupted install: write only differing files, then the manifest (run as pi5)."""
from pathlib import Path
import hashlib, json, zipfile

root = Path('/home/pi5/aerothon_ws').resolve()
archive = Path('/home/pi5/aerothon-deploy/runtime-rulebook-20261015.zip')
sha = lambda b: hashlib.sha256(b).hexdigest()
with zipfile.ZipFile(archive) as z:
    manifest = json.loads(z.read('runtime_manifest.json'))
    written = []
    for n, h in manifest['files'].items():
        target = root / n
        assert target.resolve().is_relative_to(root)
        if not target.is_file() or sha(target.read_bytes()) != h:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(n))
            written.append(n)
    (root / 'runtime_manifest.json').write_bytes(z.read('runtime_manifest.json'))
    bad = [n for n, h in manifest['files'].items() if sha((root / n).read_bytes()) != h]
    assert not bad, bad
print(json.dumps({'written_now': written, 'verified_files': len(manifest['files']),
                  'manifest_sha256': sha((root / 'runtime_manifest.json').read_bytes()),
                  'bundle_sha256': sha(archive.read_bytes())}))
