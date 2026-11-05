"""Recover interrupted bytes from verified later bytes and original SHA256."""
import hashlib,json,zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_banner_capture_qualification_20261007'
manifest=json.loads((out/'source_manifest.json').read_text())
later=root/'logs/reliability_banner_capture_qualification_fixed_20261007/failed_source_verified.zip'
with zipfile.ZipFile(later) as archive:data={name:archive.read(name) for name in manifest}
node='src/aerothon_perception/perception_banner/perception_banner/banner_node.py'
removed='''            self._ocr_cache = {"text": "", "text_letters": 0,
                               "text_confirmed": False, "text_reader": ""}
            self._ocr_box = None
            self._ocr_t0 = 0.0
'''
text=data[node].decode();needle='        if not self.gate.open():\n'+removed
assert text.count(needle)==1
data[node]=text.replace(needle,'        if not self.gate.open():\n').encode()
test='sim/test_banner_capture_contract.py'
text=data[test].decode().replace('from std_msgs.msg import String\n','')
start=text.index('    def test_camera_turning_away_invalidates_the_previous_word_read')
end=text.index("\n\nif __name__=='__main__'",start)
variants=[(text[:start].rstrip('\n')+'\n'*count+text[end:]).encode() for count in range(5)]
data[test]=next(value for value in variants if hashlib.sha256(value).hexdigest()==manifest[test])
original=root/'logs/reliability_render_split_corridors_s20261003_observation_repairs_20261007/recorded_source.zip'
with zipfile.ZipFile(original) as archive:data['sim/test_camera_gate.py']=archive.read('source/sim/test_camera_gate.py')
unmatched=[name for name,sha in manifest.items() if hashlib.sha256(data[name]).hexdigest()!=sha]
if unmatched:
    report=dict(source_archive_verified=False,qualification_pass=False,unmatched=unmatched,
                reason='Exact original bytes have not been recovered; partial log remains unqualified')
    (out/'interruption_review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report));raise SystemExit(1)
destination=out/'interrupted_source_verified.zip'
with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED) as archive:
    for name,content in sorted(data.items()):archive.writestr(name,content)
    archive.writestr('source_manifest.json',json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(destination) as archive:
    assert all(hashlib.sha256(archive.read(name)).hexdigest()==sha for name,sha in manifest.items())
report=dict(state='INTERRUPTED_UNQUALIFIED',full_suite_pass=False,rendered_started=False,
    source_files=len(manifest),source_archive_verified=True,
    archive_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
    archive=destination.name,first_incomplete_packaging_attempt='interrupted_source.zip',
    original_partial_log='logs/reliability_full_banner_capture_20261007.log',
    method='Inverse edits accepted only after every file matched original frozen SHA256')
(out/'interruption_review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
