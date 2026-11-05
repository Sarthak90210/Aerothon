"""Render the handoff template and verify its evidence links and source hashes."""
import hashlib
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[2]
base = root/'.scratch/simulation-reliability'
text = (base/'EXECUTIVE_HANDOFF_20261010.template.md').read_text(encoding='utf-8')
history = (base/'evidence_report_20261007.md').read_text(encoding='utf-8')
start = history.index('| Evidence | Result | Qualification limit |')
end = history.index('\n\nThe passive native contact recorder', start)
ledger = history[start:end]
issue_lines = []
for p in sorted((base/'issues').glob('*.md')):
    body = p.read_text(encoding='utf-8')
    title = next(line[2:].strip() for line in body.splitlines() if line.startswith('# '))
    status = re.search(r'^Status:\s*(.+)$', body, re.M).group(1).strip()
    issue_lines.append(f'- [{p.stem[:2]}: {title}](<{p.as_posix()}>) | {status}')
text = text.replace('{{HISTORICAL_LEDGER}}', ledger).replace('{{ISSUE_INVENTORY}}', '\n'.join(issue_lines))
links = []
def link(m):
    relative, label = m.group(1).split('|', 1)
    p = root/relative
    assert p.exists(), f'Missing handoff evidence: {relative}'
    links.append(relative)
    return f'[{label}](<{p.as_posix()}>)'
text = re.sub(r'\{\{([^{}]+)\}\}', link, text)
assert '{{' not in text
manifest = json.loads((root/'.scratch/reduced_scope_v39_candidate_20261008/source_manifest.json').read_text(encoding='utf-8'))
assert len(manifest) == 951
assert all(hashlib.sha256((root/n.replace('\\','/')).read_bytes()).hexdigest() == sha for n,sha in manifest.items())
versions = {}
for version in range(34, 40):
    p = root/f'logs/reliability_reduced_scope_v{version}_source_20261008/provenance.json'
    record = json.loads(p.read_text(encoding='utf-8'))
    sha = record['archive_sha256']
    assert sha in text, (version, sha)
    versions[f'v{version}'] = sha
out = base/'EXECUTIVE_HANDOFF_20261010.md'
out.write_text(text, encoding='utf-8')
review = dict(report=str(out), report_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
    words=len(text.split()), linked_evidence=len(links), issue_count=len(issue_lines),
    controlled_source_unchanged=True, source_files=len(manifest), historical_provenance=versions,
    qualification_complete=False, accepted_source=None,
    scope='Report integrity only; no mission, qualification test or source fix run')
(base/'handoff_report_review_20261010.json').write_text(json.dumps(review,indent=2)+'\n',encoding='utf-8')
print(json.dumps(review,indent=2))
