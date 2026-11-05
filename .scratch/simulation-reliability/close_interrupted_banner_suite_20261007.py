"""Preserve exact interrupted source; do not turn a partial suite into a pass."""
import hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_banner_capture_qualification_20261007'
manifest=json.loads((out/'source_manifest.json').read_text())
node='src/aerothon_perception/perception_banner/perception_banner/banner_node.py'
removed="""            self._ocr_cache = {"text": "", "text_letters": 0,
                               "text_confirmed": False, "text_reader": ""}
            self._ocr_box = None
            self._ocr_t0 = 0.0
"""
data=(root/node).read_text();needle='        if not self.gate.open():\n'+removed
assert data.count(needle)==1
reconstructed={node:data.replace(needle,'        if not self.gate.open():\n').encode()}
test='sim/test_banner_capture_contract.py'
data=(root/test).read_text().replace('from std_msgs.msg import String\n','')
start=data.index('    def test_camera_turning_away_invalidates_the_previous_word_read')
end=data.index("\n\nif __name__=='__main__'",start)
variants=[(data[:start].rstrip('\n')+'\n'*count+data[end:]).encode() for count in range(5)]
reconstructed[test]=next(value for value in variants if hashlib.sha256(value).hexdigest()==manifest[test])
original=root/'logs/reliability_render_split_corridors_s20261003_observation_repairs_20261007/recorded_source.zip'
with zipfile.ZipFile(original) as z:
    reconstructed['sim/test_camera_gate.py']=z.read('source/sim/test_camera_gate.py')
archive=out/'interrupted_source_verified.zip'
for name,sha in manifest.items():
    assert hashlib.sha256(reconstructed.get(name,(root/name).read_bytes())).hexdigest()==sha,name
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
    for name,sha in sorted(manifest.items()):
        data=reconstructed.get(name)
        if data is None:data=(root/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==sha,name
        z.writestr(name,data)
    z.writestr('source_manifest.json',json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(archive) as z:
    assert all(hashlib.sha256(z.read(name)).hexdigest()==sha for name,sha in manifest.items())
report=dict(state='INTERRUPTED_UNQUALIFIED',full_suite_pass=False,rendered_started=False,
    reason='Four camera-gate fixtures used unstamped images; stopped owned suite before rerunning corrected fixtures',
    source_files=len(manifest),source_archive_verified=True,
    archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    archive=archive.name,first_incomplete_packaging_attempt='interrupted_source.zip',
    original_partial_log='logs/reliability_full_banner_capture_20261007.log')
(out/'interruption_review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
