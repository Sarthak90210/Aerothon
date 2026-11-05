#!/usr/bin/env bash
set -euo pipefail
root='/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
stage="$(mktemp -d /tmp/aerothon-pi-bundle.XXXXXX)"
export AEROTHON_VALIDATION_ROOT="$stage"
export AEROTHON_VALIDATION_ZIP="${AEROTHON_VALIDATION_ZIP:-$root/logs/pi-runtime-with-wiring-validation-20261013.zip}"
python3 - <<'PY'
import hashlib,json,os,zipfile
from pathlib import Path
stage=Path(os.environ['AEROTHON_VALIDATION_ROOT'])
with zipfile.ZipFile(os.environ['AEROTHON_VALIDATION_ZIP']) as z:
    assert z.testzip() is None
    manifest=json.loads(z.read('runtime_manifest.json'))
    for name,digest in manifest['files'].items():
        assert hashlib.sha256(z.read(name)).hexdigest()==digest
        assert not name.startswith(('sim/','logs/','.scratch/','tests/','src/aerothon_sim/'))
    assert sorted(n for n in z.namelist() if n.endswith('.md'))==['AGENTS.md','MASTER_DOCUMENTATION.md']
    for name in z.namelist():
        assert (stage/name).resolve().is_relative_to(stage.resolve())
    z.extractall(stage)
print(f'Extracted verified runtime bundle into {stage}')
PY
cd "$stage"
set +u
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install > "$root/logs/pi_bundle_isolated_build_20261013.log" 2>&1
source install/setup.bash
set -u
ros2 launch mission_bringup mission2.launch.py --show-args > "$root/logs/pi_bundle_launch_args_20261013.log" 2>&1
python3 - <<'PY'
import importlib
from ament_index_python.packages import get_package_share_directory
import xacro
from pathlib import Path
mods=['mission_bt.mission_tree','mission_bt.mav_commander',
      'avoidance.velocity_controller','avoidance.fast_connected_planner_candidate',
      'winch_ctrl.winch_node','camera_ctrl.camera_ctrl_node',
      'perception_qr.qr_node','perception_banner.banner_node',
      'perception_redzone.redzone_node','perception_redzone.payload_node',
      'perception_overlay.overlay_node','gcs_aggregator.aggregator','gcs_aggregator.readiness_node']
for name in mods:
    module=importlib.import_module(name)
    assert '/aerothon-pi-bundle.' in module.__file__, (name,module.__file__)
    print('Imported isolated runtime:',name)
urdf=Path(get_package_share_directory('uav_description'))/'urdf/uav.urdf.xacro'
xml=xacro.process_file(str(urdf),mappings={'airframe':'cad'}).toxml()
assert 'ardupilot_gazebo' not in xml
print('CAD URDF expands without simulator meshes')
PY
printf '%s\n' "$stage" > "$root/.scratch/pi_consolidation_20261013/isolated_bundle_path.txt"
tail -5 "$root/logs/pi_bundle_isolated_build_20261013.log"
