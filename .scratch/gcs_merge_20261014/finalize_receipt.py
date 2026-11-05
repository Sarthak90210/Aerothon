"""Record this GCS software verification without making flight claims."""
import hashlib
import json
import re
import subprocess
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DIST = ROOT / 'src/aerothon_gcs/tauri_app/dist'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))


def served(path):
    rel = path.relative_to(DIST).as_posix()
    url = 'http://localhost:8899/' + urllib.parse.quote(rel)
    with urllib.request.urlopen(url, timeout=10) as response:
        body = response.read()
        assert response.status == 200, url
    assert hashlib.sha256(body).hexdigest() == digest(path), url
    return rel


baseline = read('baseline.json')
changed_decisions = [rel for rel, value in baseline['flight_decision_files'].items()
                     if not (ROOT / rel).is_file() or digest(ROOT / rel) != value]
assert not changed_decisions, changed_decisions
bundle = OUT / 'runtime-final.zip'
with zipfile.ZipFile(bundle) as archive:
    assert archive.testzip() is None
    manifest = json.loads(archive.read('runtime_manifest.json'))
    for rel, value in manifest['files'].items():
        assert hashlib.sha256(archive.read(rel)).hexdigest() == value, rel
        disk = DIST / rel[4:] if rel.startswith('gcs/') else ROOT / rel
        assert digest(disk) == value, rel
    markdown = sorted(rel for rel in archive.namelist() if rel.endswith('.md'))
    assert markdown == ['AGENTS.md', 'MASTER_DOCUMENTATION.md']
assets = sorted(path for path in DIST.rglob('*') if path.is_file())
with ThreadPoolExecutor(max_workers=4) as pool:
    http_checked = list(pool.map(served, assets))
source_hashes = {rel: value for rel, value in manifest['files'].items()
                 if not rel.startswith('gcs/')}
extra = [ROOT / 'scripts/run_tests.sh', ROOT / 'scripts/set_stream_rates.py',
         ROOT / 'scripts/export_gcs_contract.py', ROOT / 'scripts/package_pi_runtime.py',
         ROOT / 'sim/test_gcs_aggregator.py', ROOT / 'sim/test_gcs_merge_contract.py']
frontend = ROOT / 'src/aerothon_gcs/tauri_app'
extra.extend(path for folder in ['src', 'tests'] for path in (frontend / folder).rglob('*')
             if path.is_file())
extra.extend(frontend / name for name in ['package.json', 'package-lock.json',
                                        'tsconfig.json', 'vite.config.ts', 'index.html'])
for path in extra:
    if path.is_file():
        source_hashes[path.relative_to(ROOT).as_posix()] = digest(path)
source_hashes = dict(sorted(source_hashes.items()))
source_version = hashlib.sha256(json.dumps(source_hashes, sort_keys=True,
                                          separators=(',', ':')).encode()).hexdigest()
scope = read('quiet-offline-scope.json')
log = (OUT / 'quiet-full.log').read_text(encoding='utf-8')
assert '1927 passed, 8 skipped' in log
assert 'ALL IN-SCOPE OFFLINE CHECKS PASSED' in log
assert re.search(r'pass 25\b', log)
ros = read('ros-websocket-result.json')
assert ros['passed'] is True
http = read('http-command.json')
request = http['request']['data']
assert re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',
                    request['cmd_id'])
assert request['cmd'] == 'set_target'
receipt = {
    'schema': 'aerothon-gcs-software-verification/1',
    'client_date': '2026-10-14',
    'status': 'completed_gcs_software_scope',
    'scope': 'Restore the plain GCS in main, remove the old maintained HUD, and integrate with the existing production ROS command and telemetry interfaces.',
    'branch': subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
    'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'working_tree_dirty': True,
    'source_version_sha256': source_version,
    'source_files_sha256': source_hashes,
    'flight_decision_baseline': 'baseline.json',
    'changed_flight_decision_files': changed_decisions,
    'recovery_archive': {'path': 'before-merge.zip', 'sha256': digest(OUT / 'before-merge.zip')},
    'old_maintained_frontend_removed': ['src/aerothon_gcs/tauri_app/src/render.ts'],
    'configuration': {
        'ui': 'Flight operations and Testing; camera, actual SLAM, map and graphs',
        'telemetry': 'Page hostname port 8765, configurable saved browser WebSocket endpoint',
        'video': 'Selected WebSocket hostname port 8080',
        'local_preview': 'http://localhost:8899/',
        'browser_connection': 'Disconnected; no physical FCU or production flight stack started',
        'ros_contract_check': {'domain_id': 196, 'websocket_port': 18765,
                               'sensor_publishers': 'Typed test fixtures, not flight measurements'},
        'intranet_http_check': {'page': 'http://192.168.0.100:8998/',
                                'websocket_port': 18766,
                                'actuation': 'Isolated command sink; no hardware'},
        'flight_acceptance_thresholds_changed': False,
    },
    'verification': {
        'focused_python': {'passed': 99, 'log': 'focused.log'},
        'final_offline': {'passed': 1927, 'skipped': 8, 'failed': 0,
                          'duration_s': 667.77, 'exit_code': 0,
                          'log': 'quiet-full.log', 'scope_ledger': 'quiet-offline-scope.json',
                          'excluded_tests': scope['excluded_tests'],
                          'additional_skips': 'Three missing real-photo corpus tests; not passes'},
        'frontend': {'passed': 25, 'failed': 0, 'typescript': 'passed',
                     'production_build': 'passed', 'log': 'quiet-full.log'},
        'syntax_xml_yaml': 'passed',
        'typed_ros_websocket': {'passed': True, 'checks': ros['checks'],
                                'result': 'ros-websocket-result.json'},
        'plain_http_command': {'passed': True, 'result': 'http-command.json',
                               'screenshot': 'http-intranet.png',
                               'command_id': request['cmd_id']},
        'served_build_assets': {'passed': True, 'count': len(http_checked),
                                 'paths': http_checked, 'all_hashes_match_disk': True},
        'final_browser': {'map': 'Loaded bundled offline imagery',
                          'graphs': 'Flight and Sensors views loaded, unavailable data explicit',
                          'arena': 'All twenty production dimensions available offline',
                          'screenshots': ['gcs.png', 'arena.png', 'sensors.png']},
    },
    'preserved_failed_trials': [{
        'log': 'full.log', 'passed': 1926, 'failed': 1, 'skipped': 8,
        'failure': 'Existing banner detector camera-rate benchmark: about 214 ms/frame, limit 100 ms/frame. No threshold change.',
        'additional_environment_failure': 'WSL build initially had only the Windows esbuild native module; corrected ignored node_modules with matching Linux native versions.',
        'followup': 'Under-load probe failures preserved. Quiet unchanged detector class passed 11 tests; final quiet complete suite passed.',
    }],
    'bundle': {'path': bundle.name, 'sha256': digest(bundle), 'bytes': bundle.stat().st_size,
               'payload_files': len(manifest['files']), 'local_ros_packages': manifest['local_ros_packages'],
               'maintained_markdown': markdown, 'integrity_and_disk_hash_match': True},
    'limitations_and_unresolved': [
        'No Pi deployment performed in this GCS merge turn.',
        'No FCU, transmitter takeover, SITL/Gazebo movement, camera actuation or physical mechanism qualification performed in this turn.',
        'The broader proposed standalone SLAM, manual transmitter avoidance and parameterized GPS delivery supervisors are not in the existing task registry.',
        'Command acknowledgement proves dispatch only, not physical completion; command ID deduplication lasts the aggregator process lifetime.',
        'Field clearance remains unresolved: latest combined-banner cleanup run failed 21/22, native minimum 0.663645 m against 0.70 m.',
        'Strong gust and coupled delayed control failures remain preserved, unresolved and excluded; original 200-case qualification and campaign closure are not claimed.',
        'Pi GPIO encoder winch backend and physical calibration remain pending.',
        'Three missing real-photo corpus tests remain unqualified.',
    ],
    'flight_evidence_preserved': ['logs/pi_cleanup_hard_field_both_s20261004_retry1_20261013',
                                'logs/pi_cleanup_source_with_wiring_final_20261013'],
    'flight_qualified': False,
    'original_200_case_qualified': False,
}
(OUT / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'receipt': str(OUT / 'result.json'), 'source_version_sha256': source_version,
                  'served_assets': len(http_checked), 'bundle_sha256': digest(bundle),
                  'changed_flight_decision_files': changed_decisions}, indent=2))
