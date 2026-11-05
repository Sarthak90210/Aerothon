"""Archive exact recorded source, refusing changed inputs or altered assets."""
import hashlib, json, sys, zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
out = Path(sys.argv[1]).resolve()
dest = out/'recorded_source.zip'
if dest.exists():
    raise SystemExit('Source archive already exists')
runtime = json.loads((out/'runtime_configuration_manifest.json').read_text())['sha256']
for name, expected in runtime.items():
    if hashlib.sha256((out/name).read_bytes()).hexdigest() != expected:
        raise SystemExit('Recorded runtime asset changed: '+name)
sources = {}
for manifest in ('source_manifest.json','qualification_tools_manifest.json'):
    for name, expected in json.loads((out/manifest).read_text()).items():
        path = Path(name)
        if not path.is_absolute():
            path = root/path
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise SystemExit('Source changed since recording: '+name)
        rel = path.relative_to(root).as_posix()
        sources[rel] = (data, expected)
with zipfile.ZipFile(dest, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as z:
    for rel, (data, _) in sources.items():
        z.writestr('source/'+rel, data)
    z.writestr('archive_manifest.json', json.dumps({k:v[1] for k,v in sources.items()}, indent=2))
with zipfile.ZipFile(dest) as z:
    for rel, (_, expected) in sources.items():
        if hashlib.sha256(z.read('source/'+rel)).hexdigest() != expected:
            raise SystemExit('Archive verification failed: '+rel)
report = dict(source_files=len(sources), runtime_assets_verified=len(runtime),
              archive=dest.name, archive_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
              archive_verified=True)
(out/'source_archive_verification.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
