"""Recover previous bytes only when they match the frozen failure hashes."""
import hashlib,json,re,zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_banner_capture_qualification_fixed_20261007'
manifest=json.loads((out/'source_manifest.json').read_text())
current=root/'logs/reliability_banner_capture_qualification_continuity_20261007/frozen_source.zip'
with zipfile.ZipFile(current) as archive:
    data={name:archive.read(name) for name in manifest}
name='src/aerothon_perception/perception_banner/perception_banner/banner_node.py'
node=data[name].decode()
start=node.index('    @staticmethod\n    def _regions_overlap(')
end=node.index('    def green_mask(',start)
node=node[:start]+node[end:]
node=node.replace('def green_mask(self, frame, allow_clipped=True):','def green_mask(self, frame):')
start=node.index('        if allow_clipped:\n')
end=node.index('        mask = cv2.morphologyEx',start)
node=node[:start]+node[end:]
node=node.replace('board[0]:board[0] + board[2]],\n                                allow_clipped=False)',
                  'board[0]:board[0] + board[2]])')
node=node.replace('        lettered_candidates = []\n','')
start=node.index('            if info.get("board_area_px") is not None:\n')
end=node.index('\n            if ok and best is None:',start)
node=node[:start]+node[end:]
start=node.index('        if (self._ocr_cache.get("text_confirmed")\n')
end=node.index('        if read_box is None:',start)
node=node[:start]+node[end:]
data[name]=node.encode()

name='sim/test_banner_capture_contract.py'
test=data[name].decode().replace('import numpy as np\n','')
test=test.replace('        return self.feed_image(image)\n\n    def feed_image(self,image):\n','')
start=test.index('    def test_clipped_board_is_read_from_a_cold_start(')
end=test.index('    def test_a_previous_word_read_cannot_identify_a_blank_current_frame(',start)
test=test[:start]+test[end:]
data[name]=test.encode()

name='sim/test_perception_corruption.py'
test=data[name].decode()
start=test.index('        # Each corruption is an independent readability trial.')
end=test.index('        message = self.bridge.cv2_to_imgmsg',start)
test=test[:start]+test[end:]
test=test.replace('        message = self.bridge.cv2_to_imgmsg(img, "bgr8")\n'
                  '        message.header.stamp = self.node.get_clock().now().to_msg()\n'
                  '        self.node.on_image(message)',
                  '        self.node.on_image(self.bridge.cv2_to_imgmsg(img, "bgr8"))')
data[name]=test.encode()

name='sim/test_phase0_rails.py'
test=data[name].decode().replace('        captured = self.node.get_clock().now().nanoseconds * 1e-9\n','')
test=test.replace(', "capture_stamp": captured,\n             "processed_stamp": captured','')
data[name]=test.encode()

unmatched=[name for name,sha in manifest.items() if hashlib.sha256(data[name]).hexdigest()!=sha]
if unmatched:
    print(json.dumps(dict(archive_verified=False,unmatched=unmatched)))
    for name in unmatched:
        (out/('reconstruction_'+Path(name).name)).write_bytes(data[name])
    raise SystemExit(1)
destination=out/'failed_source_verified.zip'
with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED) as archive:
    for name,content in sorted(data.items()):archive.writestr(name,content)
    archive.writestr('source_manifest.json',json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(destination) as archive:
    assert all(hashlib.sha256(archive.read(name)).hexdigest()==sha for name,sha in manifest.items())
review=dict(source_files=len(manifest),archive_verified=True,qualification_pass=False,
    archive_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
    method='Inverse edits accepted only after every file matched original frozen SHA256')
(out/'source_archive_review.json').write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps(review))
