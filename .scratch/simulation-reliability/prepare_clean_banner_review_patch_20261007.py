"""Save a complete one-file repair for review; do not touch active production."""
import difflib,hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
name='src/aerothon_perception/perception_banner/perception_banner/banner_node.py'
path=root/name;before=path.read_text()
override=root/'logs/reliability_clean_banner_pixels_contract_20261007/source_override'
old=(override/'original_on_image.py').read_text();new=(override/'candidate_on_image.py').read_text()
def indent(text):return ''.join('    '+line if line.strip() else line for line in text.splitlines(keepends=True))
assert before.count(indent(old))==1
after=before.replace(indent(old),indent(new))
out=root/'logs/reliability_clean_banner_review_patch_20261007';out.mkdir(exist_ok=False)
(out/'banner_node.py.before').write_bytes(path.read_bytes())
(out/'banner_node.py.candidate').write_text(after)
(out/'change.patch').write_text(''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name)))
report=dict(production_modified=False,base_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    candidate_sha256=hashlib.sha256((out/'banner_node.py.candidate').read_bytes()).hexdigest(),
    source_file=name,scope='Reviewable one-file patch; full suite and fresh native qualification remain required')
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
