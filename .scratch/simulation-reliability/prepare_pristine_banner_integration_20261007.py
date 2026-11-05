"""Prepare two reviewable file changes and the next exact-source qualifier."""
import ast,difflib,hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];here=Path(__file__).parent
review=root/'logs/reliability_clean_banner_review_patch_20261007'
test_name='sim/test_banner_capture_contract.py';test=root/test_name
before=test.read_text()
anchor='    def test_duplicate_image_capture_does_not_generate_new_evidence(self):'
assert before.count(anchor)==1
method='''    def test_display_annotations_never_enter_the_word_reader(self):
        image=cv2.imread(str(ROOT/'tests/fixtures/banner_sim_ambient_3m.png'))
        self.assertIsNotNone(image)
        namespace=self.node.on_image.__func__.__globals__
        normalized=namespace['normalise'](image.copy())
        reader=namespace['reads_banner']
        calls=[]
        def observed_reader(sub,*args,**kwargs):
            x,y,w,h=self.node._ocr_box
            self.assertTrue(np.array_equal(sub,normalized[y:y+h,x:x+w]),
                            'OCR received display pixels absent from the camera')
            calls.append((x,y,w,h))
            return reader(sub,*args,**kwargs)
        namespace['reads_banner']=observed_reader
        try:
            self.feed_image(image)
        finally:
            namespace['reads_banner']=reader
        self.assertTrue(calls,'The fixture must exercise the actual word reader')

'''
after=before.replace(anchor,method+anchor);ast.parse(after)
(review/'test_banner_capture_contract.py.before').write_bytes(test.read_bytes())
(review/'test_banner_capture_contract.py.candidate').write_text(after)
(review/'test_change.patch').write_text(''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/'+test_name,tofile='b/'+test_name)))
report=json.loads((review/'report.json').read_text())
report['test_change']=dict(source_file=test_name,base_sha256=hashlib.sha256(test.read_bytes()).hexdigest(),
    candidate_sha256=hashlib.sha256((review/'test_banner_capture_contract.py.candidate').read_bytes()).hexdigest())
ast.parse((review/'banner_node.py.candidate').read_text())
(review/'report.json').write_text(json.dumps(report,indent=2)+'\n')
template=(here/'qualify_banner_capture_continuity_20261007.py').read_text()
start=template.index('def manifest():');end=template.index('\ndef write(',start)
template=template[:start]+'from fast_acceptance_source_manifest_20261007 import manifest\n\n'+template[end:]
template=template.replace('reliability_banner_capture_qualification_continuity_20261007','reliability_pristine_banner_qualification_20261007')
template=template.replace('banner_capture_continuity_20261007','pristine_banner_pixels_20261007')
template=template.replace("'headless capture metadata'","'headless capture metadata','pristine analysis pixels and separate display overlays'")
anchor="    (OUT/'source_manifest.json').write_text(json.dumps(frozen,indent=2)+'\\n')"
assert template.count(anchor)==1
archive_call="""\n    assert run(['/mnt/c/Python314/python.exe',
        r'D:\\MY DOCUMENTS\\VIT\\Team Rotor Fpv\\AEROTHON\\.scratch\\simulation-reliability\\archive_qualification_source_20261007.py',
        'logs/reliability_pristine_banner_qualification_20261007'],OUT/'initial_source_archive.log')==0"""
template=template.replace(anchor,anchor+archive_call)
target=here/'qualify_pristine_banner_20261007.py';assert not target.exists();target.write_text(template)
print(json.dumps(dict(production_modified=False,prepared_files=2,qualifier=str(target))))
