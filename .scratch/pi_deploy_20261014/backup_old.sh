set -euo pipefail
test "$(id -u)" = 0
backup=/home/pi5/aerothon-previous-20261014.tar.gz
test ! -e "$backup"
systemctl stop aerothon-gcs-standalone aerothon-telemetry-streams aerothon-mavlink-router
if pgrep -af '/home/pi5/sitl-disposable/(bin/arducopter|supervisor.py)' ; then
    echo 'A disposable simulator is active; resolve its owned process before archiving.' >&2
    exit 1
fi
paths=(home/pi5/aerothon-gcs-standalone home/pi5/sitl-disposable
       home/pi5/.local/state/aerothon-gcs-standalone home/pi5/src/mavlink-router
       home/pi5/pixhawk-router.conf home/pi5/pixhawk-router.d
       home/pi5/config-uart0.new home/pi5/config-bec-cap.new
       home/pi5/fcu-status-probe.py home/pi5/pi_router_probe.py
       home/pi5/aerothon-gcs-standalone.service.new
       home/pi5/aerothon-mavlink-router.service.new
       home/pi5/aerothon-telemetry-streams.service.new
       etc/systemd/system/aerothon-gcs-standalone.service
       etc/systemd/system/aerothon-mavlink-router.service
       etc/systemd/system/aerothon-telemetry-streams.service
       boot/firmware/config.txt boot/firmware/cmdline.txt)
[[ ! -d /home/pi5/.aerothon ]] || paths+=(home/pi5/.aerothon)
tar --exclude='home/pi5/sitl-disposable/venv' --exclude='*/.git' \
    -czf "$backup" -C / "${paths[@]}"
tar -tzf "$backup" >/dev/null
chown pi5:pi5 "$backup"
sha256sum "$backup"
ls -lh "$backup"
install -d -o pi5 -g pi5 /home/pi5/aerothon-deploy
