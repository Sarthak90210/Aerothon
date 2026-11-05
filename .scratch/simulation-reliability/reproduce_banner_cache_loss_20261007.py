"""Differential replay of real saved camera fixtures; no flight inputs."""
import hashlib,json,sys,time,types,zipfile
from pathlib import Path
import cv2,rclpy
from cv_bridge import CvBridge
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'src/aerothon_perception/perception_banner'))
from perception_banner.banner_node import BannerNode
archive=root/'logs/reliability_render_split_corridors_s20261003_observation_repairs_20261007/recorded_source.zip'
name='src/aerothon_perception/perception_banner/perception_banner/banner_node.py'
with zipfile.ZipFile(archive) as z:
    data=z.read('source/'+name)
    manifest=json.loads((archive.parent/'source_manifest.json').read_text())
    assert hashlib.sha256(data).hexdigest()==manifest[name]
old=types.ModuleType('frozen_banner_cache_replay');sys.modules[old.__name__]=old
exec(compile(data,name,'exec'),old.__dict__)
out=root/'logs/reliability_banner_cache_differential_20261007';out.mkdir(exist_ok=False)
rclpy.init();results=[]
try:
    for label,cls in [('preserved_split_source',old.BannerNode),('capture_and_cache_repair',BannerNode)]:
        node=cls();details=[]
        node.pub.publish=lambda _:None
        node.pub_detail.publish=lambda message:details.append(json.loads(message.data))
        try:
            for image in ('banner_sim_ambient_3m.png','banner_absent_horizon.png'):
                pixels=cv2.imread(str(root/'tests/fixtures'/image));assert pixels is not None
                message=CvBridge().cv2_to_imgmsg(pixels,encoding='bgr8')
                message.header.stamp=node.get_clock().now().to_msg()
                node.on_image(message)
                if len(details)==1:
                    assert details[-1]['text_confirmed'],'Initial real fixture did not establish a word read'
                    node._ocr_t0=time.monotonic()
            results.append(dict(source=label,initial=details[0],blank_current_frame=details[1]))
        finally:node.destroy_node()
finally:rclpy.shutdown()
assert results[0]['blank_current_frame']['identified'] is True,'Preserved defect not reproduced'
assert results[1]['blank_current_frame']['identified'] is False,'Repair still identifies absent board'
report=dict(results=results,baseline_defect_reproduced=True,repair_rejects_blank_frame=True,
    source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    scope='Sequential replay of saved camera fixtures; not a rendered flight or hardware qualification')
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
(out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(baseline_defect_reproduced=True,repair_rejects_blank_frame=True)))
