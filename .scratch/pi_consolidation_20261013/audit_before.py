import ast
import hashlib
import json
import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
skip = {'.git', 'node_modules', '__pycache__', 'build', 'install', 'log', 'logs', 'evidence', '.pytest_cache', 'dist', 'target'}
sources = {}
docs = []
unused = []
for directory in ('src', 'scripts', 'sim', 'tests', 'docs', '.scratch', '.agents'):
    for current, dirs, files in os.walk(ROOT / directory):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in files:
            p = Path(current) / name
            rel = p.relative_to(ROOT).as_posix()
            if p.suffix == '.md':
                docs.append(p)
            if directory in ('src', 'scripts', 'sim'):
                sources[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
            if directory == 'src' and p.suffix == '.py':
                tree = ast.parse(p.read_text(encoding='utf-8-sig'))
                loads = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
                for n in ast.walk(tree):
                    if isinstance(n, (ast.Import, ast.ImportFrom)):
                        for a in n.names:
                            binding = a.asname or a.name.split('.')[0]
                            if binding not in loads and binding != '*':
                                unused.append(dict(file=rel, line=n.lineno, binding=binding,
                                                   module=getattr(n, 'module', None), review_required=True))
docs += list(ROOT.glob('*.md'))
archive = OUT / 'historical_documentation.zip'
if archive.exists():
    raise SystemExit('Archive already exists; original evidence must be preserved')
with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted(set(docs)):
        z.write(p, p.relative_to(ROOT).as_posix())
doc_receipt = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(docs))}
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for rel, sha in doc_receipt.items():
        assert hashlib.sha256(z.read(rel)).hexdigest() == sha
(OUT / 'baseline.json').write_text(json.dumps(dict(sources=sources, documentation=doc_receipt,
    archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), unused_import_candidates=unused), indent=2), encoding='utf-8')
print(json.dumps(dict(source_files=len(sources), archived_markdown=len(doc_receipt),
    unused_import_candidates=len(unused), archive=str(archive)), indent=2))
