import gzip
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[2]
here = Path(__file__).resolve().parent
package = json.loads((here / 'package_result.json').read_text(encoding='utf-8-sig'))
archive = Path(package['bundle'])
assert hashlib.sha256(archive.read_bytes()).hexdigest() == package['sha256']
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    manifest = json.loads(z.read('runtime_manifest.json'))
    for name, digest in manifest['files'].items():
        assert hashlib.sha256(z.read(name)).hexdigest() == digest
    assert sorted(n for n in z.namelist() if n.endswith('.md')) == ['AGENTS.md', 'MASTER_DOCUMENTATION.md']
    assert len(manifest['local_ros_packages']) == 13
    compressed = [n for n in z.namelist() if n.startswith('gcs/assets/') and n.endswith('.gz')]
    for name in compressed:
        assert gzip.decompress(z.read(name)) == z.read(name[:-3])
    assert z.read('MASTER_DOCUMENTATION.md') == (root / 'MASTER_DOCUMENTATION.md').read_bytes()

offline = (here / 'offline_checks.log').read_text()
assert '2103 passed, 8 skipped' in offline
assert '12 passed' in offline
assert 'ALL IN-SCOPE OFFLINE CHECKS PASSED' in offline
assert 'tests 45' in (here / 'frontend_tests.log').read_text()
source_paths = ['MASTER_DOCUMENTATION.md',
    *['src/aerothon_gcs/tauri_app/src/' + p for p in ['App.tsx','LidarView.tsx','gcs.css','lidarGeometry.ts','slamViewport.ts','types.ts']],
    'src/aerothon_payload/winch_ctrl/winch_ctrl/winch_node.py',
    'src/aerothon_runtime/aerothon_runtime/execution_node.py',
    'sim/test_winch.py','sim/test_gcs_merge_contract.py',
    'src/aerothon_gcs/tauri_app/tests/lidarGeometry.test.mjs',
    'src/aerothon_gcs/tauri_app/tests/slamViewport.test.mjs']
receipt = dict(date='2026-10-19',status='ready for props-off Pi installation/build and bench verification',
    scope='SLAM display redesign, freshness/frame/mounting correctness, local GCS testing continuation and winch refusal/receipt fixes',
    package=package,
    verified=dict(payload_hashes=len(manifest['files']),local_ros_packages=13,markdown_files=2,
        gzip_assets=len(compressed),served_http=200,served_bundle='index-BvJeOAWo.js',
        offline_passed=2103,offline_skipped=8,native_ros_passed=12,frontend_passed=45,affected_backend_passed=51,
        mounting_reference_cases=80,mounting_max_error_m=3.972054645195637e-15),
    skip_scope=['5 deferred strong-gust cases','3 tests lacking photographed perception corpus'],
    browser=dict(performance=json.loads((here/'browser_performance.json').read_text()),
        checks=['light/dark themes','390px viewport, no horizontal overflow after header fix',
            'explicit follow, keyboard pan cancels follow, layer switches',
            'fresh map with paused lidar: 0 cyan map-overlay pixels',
            'old pose: registered overlay hidden','held mapping: backend reason visible',
            'actual local Gazebo/SITL map, independent of synthetic fixture'],
        preview='slam-ui-preview.jpg',preview_data='synthetic ROS display fixture, not hardware'),
    source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in source_paths},
    deployment=dict(pi_accessed=False,pi_deployed=False,arm64_build_verified=False,hardware_qualified=False),
    remaining=['Pi ARM64 build and live sensor/mount verification',
        'avoidance route made insufficient progress; interrupted and recovered',
        'full mission stalled at banner alignment; interrupted and recovered',
        '7m GPS delivery refused actuator capabilities before arming',
        'delivery here reached WinchDrop but load calibration was unqualified'],
    local_testing='local_testing.json',shutdown='local_shutdown.json',research='research.json')
(here/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(status=receipt['status'],bundle_verified=True,sha256=package['sha256'],checks=receipt['verified'])))
