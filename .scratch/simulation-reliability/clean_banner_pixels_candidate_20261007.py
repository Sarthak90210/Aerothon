"""Keep display overlays out of camera analysis and OCR inputs."""
import inspect,textwrap
from pathlib import Path

def install(node_class,evidence):
    original=node_class.on_image
    before=textwrap.dedent(inspect.getsource(original));after=before
    old='h, w = frame.shape[:2]'
    assert after.count(old)==1
    after=after.replace(old,'overlay = frame.copy()\n    '+old)
    replacements={
        'cv2.rectangle(frame,':'cv2.rectangle(overlay,',
        'cv2.putText(frame,':'cv2.putText(overlay,',
        "self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')":"self.bridge.cv2_to_imgmsg(overlay, encoding='bgr8')",
        '# The boxes above are drawn regardless -- the OCR reads from this same':
            '# Display boxes are separate from the image used by analysis and OCR.',
        '# frame -- but the 2.7 MB conversion is only for a GCS that watches.':
            '# Convert the overlay only when the GCS is watching.',
    }
    for old,new in replacements.items():
        assert old in after,old;after=after.replace(old,new)
    evidence.mkdir(exist_ok=False)
    (evidence/'original_on_image.py').write_text(before)
    (evidence/'candidate_on_image.py').write_text(after)
    namespace=dict(original.__globals__)
    exec(compile(after,str(evidence/'candidate_on_image.py'),'exec'),namespace)
    node_class.on_image=namespace['on_image']
    return original
