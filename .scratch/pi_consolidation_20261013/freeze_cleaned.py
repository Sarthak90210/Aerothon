"""Freeze cleaned source and prove the narrow winch import cleanup."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'sim'))
from campaign_record import source_manifest

out = ROOT / 'logs/pi_cleanup_source_with_wiring_final_20261013'
out.mkdir(exist_ok=False)
baseline = json.loads((Path(__file__).parent / 'baseline.json').read_text())
python_changes = [rel for rel, digest in baseline['sources'].items()
                  if rel.startswith('src/') and rel.endswith('.py')
                  and hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != digest]
winch = 'src/aerothon_payload/winch_ctrl/winch_ctrl/winch_node.py'
assert python_changes == [winch], python_changes
before = ast.parse(subprocess.check_output(['git', 'show', f'HEAD:{winch}'], cwd=ROOT).decode())
after = ast.parse((ROOT / winch).read_text(encoding='utf-8-sig'))
for node in ast.walk(before):
    if isinstance(node, ast.ImportFrom) and node.module == 'std_msgs.msg':
        node.names = [name for name in node.names if name.name != 'Empty']
assert ast.dump(before, include_attributes=False) == ast.dump(after, include_attributes=False)
manifest = source_manifest(ROOT)
manifest.update({rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
                 for rel in ('MASTER_DOCUMENTATION.md', 'AGENTS.md')})
(out / 'source_manifest.json').write_text(json.dumps(manifest, indent=2))
with zipfile.ZipFile(out / 'frozen_source.zip', 'x', compression=zipfile.ZIP_DEFLATED) as z:
    for rel in sorted(manifest):
        z.write(ROOT / rel, rel)
receipt = dict(candidate='V44 behavior-preserving cleanup', accepted_source=False,
               archive_sha256=hashlib.sha256((out / 'frozen_source.zip').read_bytes()).hexdigest(),
               controlled_files=len(manifest), runtime_python_changes=python_changes,
               winch_ast_equivalent_after_unused_import_removal=True,
               algorithm_change=False, encoder_backend_implemented=False)
(out / 'provenance.json').write_text(json.dumps(receipt, indent=2))
print(json.dumps(receipt, indent=2))
