"""Archive a coordinator's frozen source, with byte verification before/after."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

root=Path(__file__).resolve().parents[2]
out=(root/sys.argv[1]).resolve()
assert out.is_relative_to((root/'logs').resolve())
manifest=json.loads((out/'source_manifest.json').read_text())
archive_path=out/'frozen_source.zip'
with zipfile.ZipFile(archive_path,'x',compression=zipfile.ZIP_DEFLATED) as archive:
    for name,sha in sorted(manifest.items()):
        path=(root/name).resolve()
        assert path.is_relative_to(root.resolve()),name
        data=path.read_bytes()
        assert hashlib.sha256(data).hexdigest()==sha,name
        archive.writestr(name,data)
    archive.writestr('source_manifest.json',json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(archive_path) as archive:
    assert all(hashlib.sha256(archive.read(name)).hexdigest()==sha
               for name,sha in manifest.items())
review=dict(source_files=len(manifest),archive_verified=True,
            archive_sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest(),
            scope='Frozen source evidence; archive verification is not test or flight qualification')
(out/'source_archive_review.json').write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps(review))
