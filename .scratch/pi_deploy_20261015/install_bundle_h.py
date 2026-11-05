"""Install a verified runtime bundle into /home/pi5/aerothon_ws (run as pi5)."""
from pathlib import Path
import hashlib, io, json, sys, tarfile, zipfile

root = Path('/home/pi5/aerothon_ws').resolve()
deploy = Path('/home/pi5/aerothon-deploy')
archive = deploy / 'runtime-rulebook-20261016h.zip'
receipt = deploy / 'before-rulebook-20261016h.json'
backup = deploy / 'before-rulebook-20261016h.tar.gz'
if receipt.exists() or backup.exists():
    sys.exit('evidence path already exists')
sha = lambda b: hashlib.sha256(b).hexdigest()
bundle_sha = sha(archive.read_bytes())
assert bundle_sha == 'cf28285f431d20b9adeb805024893492992a8b8808e5163915d37d2f87472acc', bundle_sha
with zipfile.ZipFile(archive) as z:
    manifest = json.loads(z.read('runtime_manifest.json'))
    for name, digest in manifest['files'].items():
        if not (root / name).resolve().is_relative_to(root):
            raise RuntimeError('unsafe bundle path ' + name)
        if sha(z.read(name)) != digest:
            raise RuntimeError('bad bundle hash ' + name)
    old = json.loads((root / 'runtime_manifest.json').read_text())
    before = {n: sha((root / n).read_bytes()) for n in old['files'] if (root / n).is_file()}
    changed = [n for n, h in manifest['files'].items() if before.get(n) != h]
    removed = [n for n in old['files'] if n not in manifest['files']]
    with tarfile.open(backup, 'w:gz') as tar:
        for n in sorted(set(changed + removed + ['runtime_manifest.json'])):
            if (root / n).is_file():
                tar.add(root / n, arcname=n)
    receipt.write_text(json.dumps({'bundle': bundle_sha, 'manifest': old, 'source': before,
                                   'changed': changed, 'removed': removed}, indent=2))
    for n in removed:
        target = (root / n).resolve()
        if not target.is_relative_to(root):
            raise RuntimeError('unsafe obsolete path')
        target.unlink(missing_ok=True)
    for n in [*changed, 'runtime_manifest.json']:
        target = root / n
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(z.read(n))
    for n, h in manifest['files'].items():
        assert sha((root / n).read_bytes()) == h, n
print(json.dumps({'verified_files': len(manifest['files']), 'bundle_sha256': bundle_sha,
                  'changed': len(changed), 'removed': removed,
                  'backup_sha256': sha(backup.read_bytes())}))
