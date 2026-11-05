"""Use real OCR while verifying that its input is unchanged camera pixels."""
import hashlib,json,sys
from pathlib import Path
import cv2,numpy as np,rclpy
from cv_bridge import CvBridge
root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'src/aerothon_perception/perception_banner'),str(root/'src/aerothon_mission/mission_bt')]
from perception_banner.banner_node import BannerNode,normalise
from clean_banner_pixels_candidate_20261007 import install
out=root/'logs/reliability_clean_banner_pixels_contract_20261007';out.mkdir(exist_ok=False)
image=cv2.imread(str(root/'tests/fixtures/banner_sim_ambient_3m.png'));assert image is not None
raw=normalise(image.copy());results=[]
rclpy.init()
try:
    for kind in ('original','separate_overlay'):
        if kind=='separate_overlay':install(BannerNode,out/'source_override')
        node=BannerNode();node.pub.publish=lambda _:None;details=[]
        node.pub_detail.publish=lambda msg:details.append(json.loads(msg.data))
        namespace=node.on_image.__func__.__globals__;reader=namespace['reads_banner'];checks=[]
        def observed_reader(sub,*args,**kwargs):
            x,y,w,h=node._ocr_box
            expected=raw[y:y+h,x:x+w]
            checks.append(dict(ocr_box=[x,y,w,h],exact_camera_pixels=bool(np.array_equal(sub,expected)),
                changed_channels=int(np.count_nonzero(sub!=expected))))
            return reader(sub,*args,**kwargs)
        namespace['reads_banner']=observed_reader
        try:
            message=CvBridge().cv2_to_imgmsg(image.copy(),encoding='bgr8')
            message.header.stamp=node.get_clock().now().to_msg();node.on_image(message)
            assert checks
            if kind=='original':assert any(not row['exact_camera_pixels'] for row in checks)
            else:assert all(row['exact_camera_pixels'] for row in checks)
            results.append(dict(kind=kind,ocr_checks=checks,detail=details[-1]))
        finally:namespace['reads_banner']=reader;node.destroy_node()
finally:rclpy.shutdown()
report=dict(passed=True,cases=results,scope='Actual OCR on a saved rendered fixture; no flight qualification',
    production_modified=False,fixture_sha256=hashlib.sha256((root/'tests/fixtures/banner_sim_ambient_3m.png').read_bytes()).hexdigest())
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(passed=True,cases=[dict(kind=row['kind'],ocr_checks=row['ocr_checks']) for row in results])))
