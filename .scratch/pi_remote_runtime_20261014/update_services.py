from pathlib import Path
p=Path('scripts/pi_runtime/install_services.sh');s=p.read_text()
s=s.replace('console.launch.py Dockerfile Dockerfile.dependencies;', 'console.launch.py Dockerfile Dockerfile.dependencies profile_router.py stop_runtime.py;')
a=s.index('cat >/etc/systemd/system/aerothon-gcs.service');b=s.index("cat >/etc/systemd/system/aerothon-router.service",a)
s=s[:a]+'''cat >/etc/systemd/system/aerothon-gcs.service <<'EOF'
[Unit]
Description=AeroTHON Pi webpage and managed production runtime
Requires=docker.service
After=docker.service network.target aerothon-router.service
Conflicts=aerothon-console.service aerothon-stack.service
[Service]
ExecStart=/bin/bash /home/pi5/aerothon-deploy/run_container.sh web
ExecStop=/bin/bash -c '/usr/bin/python3 /home/pi5/aerothon-deploy/stop_runtime.py && /usr/bin/docker stop --time 30 aerothon-runtime'
Restart=on-failure
RestartSec=5
KillMode=process
TimeoutStopSec=65
[Install]
WantedBy=multi-user.target
EOF
'''+s[b:]
s=s.replace('ExecCondition=/usr/bin/test -c ${AEROTHON_FCU_DEVICE}\n','')
s=s.replace('systemctl enable aerothon-gcs.service aerothon-router.service aerothon-console.service','systemctl disable aerothon-console.service 2>/dev/null || true\nsystemctl enable aerothon-gcs.service aerothon-router.service')
s=s.replace('systemctl start aerothon-gcs.service aerothon-router.service aerothon-console.service','systemctl start aerothon-router.service aerothon-gcs.service')
p.write_text(s)
