set -euo pipefail
test "$(id -u)" = 0
expected=0bc97164f00c615d445bb6fb91ae026d3dcfb8503fadb8f2e3034d1cd32731af
test "$(sha256sum /home/pi5/aerothon-previous-20261014.tar.gz | cut -d' ' -f1)" = "$expected"
systemctl disable --now aerothon-gcs-standalone aerothon-telemetry-streams aerothon-mavlink-router
sudo -u pi5 pipx uninstall mavproxy
python3 <<'PY'
from pathlib import Path
log = Path('/home/pi5/src/mavlink-router/build/meson-logs/install-log.txt')
paths = {line for line in log.read_text().splitlines() if line and not line.startswith('#')}
assert paths == {'/usr/local/bin/mavlink-routerd', '/usr/lib/systemd/system/mavlink-router.service'}, paths
for path in paths:
    Path(path).unlink(missing_ok=True)
PY
python3 <<'PY'
from pathlib import Path
import json, shutil
root = Path('/home/pi5').resolve()
names = ['sitl-disposable', 'aerothon-gcs-standalone', '.venvs/aerothon-gcs-standalone', 'src/mavlink-router',
         'pixhawk-router.conf', 'pixhawk-router.d', 'fcu-status-probe.py', 'pi_router_probe.py',
         'config-uart0.new', 'config-bec-cap.new', 'standalone-gcs.tar.gz', 'flight-display-assets.tar.gz',
         'aerothon-gcs-standalone.service.new', 'aerothon-mavlink-router.service.new',
         'aerothon-telemetry-streams.service.new', '.local/state/aerothon-gcs-standalone']
removed = []
for name in names:
    target = (root / name).resolve()
    assert target.is_relative_to(root) and target != root, target
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink(missing_ok=True)
    removed.append(str(target))
for name in ['aerothon-gcs-standalone', 'aerothon-mavlink-router', 'aerothon-telemetry-streams']:
    (Path('/etc/systemd/system')/(name+'.service')).unlink(missing_ok=True)
Path('/home/pi5/aerothon-deploy/removed_old_files.json').write_text(json.dumps(removed, indent=2)+'\n')
PY
export DEBIAN_FRONTEND=noninteractive
apt-get purge -y thonny
systemctl daemon-reload
df -h /
