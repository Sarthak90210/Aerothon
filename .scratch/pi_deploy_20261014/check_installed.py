"""Read-only Pi runtime integrity and import verification inside its container."""
import hashlib
import importlib
import json
from pathlib import Path
import platform
import subprocess

root = Path('/workspace')
manifest = json.loads((root/'runtime_manifest.json').read_text())
for rel, digest in manifest['files'].items():
    assert hashlib.sha256((root/rel).read_bytes()).hexdigest() == digest, rel
modules = ('mission_bt.mission_tree', 'mission_bt.mav_commander',
           'avoidance.velocity_controller', 'camera_ctrl.camera_ctrl_node',
           'winch_ctrl.winch_node', 'perception_qr.qr_node',
           'perception_banner.banner_node', 'perception_redzone.redzone_node',
           'perception_redzone.payload_node', 'perception_overlay.overlay_node',
           'gcs_aggregator.aggregator', 'gcs_aggregator.readiness_node',
           'mission_bringup.stream_rate_keeper')
results = {}
for name in modules:
    module = importlib.import_module(name)
    source = Path(module.__file__).resolve()
    assert source.is_relative_to(root), source
    results[name] = str(source)
xacro = subprocess.check_output(['ros2','pkg','prefix','uav_description'], text=True).strip()
urdf = subprocess.check_output(['xacro', xacro+'/share/uav_description/urdf/uav.urdf.xacro', 'airframe:=cad'], text=True)
assert '<robot' in urdf and '<link name="base_link"' in urdf
print(json.dumps(dict(platform=platform.machine(), verified_files=len(manifest['files']), imports=results,
                      urdf_bytes=len(urdf.encode()),
                      dependencies={name: getattr(importlib.import_module(name), '__version__', 'ROS package')
                                    for name in ('cv2', 'numpy', 'websockets', 'py_trees')},
                      hardware_qualified=False), indent=2))
