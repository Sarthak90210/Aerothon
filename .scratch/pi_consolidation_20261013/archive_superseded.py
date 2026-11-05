"""Remove superseded maintained guides only after checking their archived bytes."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
baseline = json.loads((OUT / 'baseline.json').read_text())
removed = []
with zipfile.ZipFile(OUT / 'historical_documentation.zip') as z:
    assert z.testzip() is None
    for rel, digest in baseline['documentation'].items():
        # Skills are third-party developer tooling, not project documentation.
        if rel == 'AGENTS.md' or rel.startswith('.agents/'):
            continue
        path = (ROOT / rel).resolve()
        assert path.is_relative_to(ROOT.resolve()) and path.suffix == '.md'
        assert hashlib.sha256(z.read(rel)).hexdigest() == digest
        if not path.exists():
            continue
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, f'Changed since archive: {rel}'
        path.unlink()
        removed.append(dict(original_path=rel, sha256=digest,
                            archive_member=rel, reason='Superseded by two maintained guides'))
(OUT / 'documentation_cleanup.json').write_text(json.dumps(dict(removed=removed,
    retained_project_guides=['AGENTS.md', 'MASTER_DOCUMENTATION.md'],
    retained_developer_skills=True), indent=2))
print(f'Archived and removed {len(removed)} superseded project Markdown files.')
