set -euo pipefail
test "$(id -u)" = 0
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::http::Proxy=http://127.0.0.1:3128 -o Acquire::https::Proxy=http://127.0.0.1:3128 -o Acquire::Retries=2 -o Acquire::http::Timeout=30 update
apt-get -o Acquire::http::Proxy=http://127.0.0.1:3128 -o Acquire::https::Proxy=http://127.0.0.1:3128 install -y --no-install-recommends docker.io docker-cli python3-serial
install -d /run/systemd/system/docker.service.d
cat >/run/systemd/system/docker.service.d/aerothon-install-proxy.conf <<'EOF'
[Service]
Environment="HTTP_PROXY=http://127.0.0.1:3128" "HTTPS_PROXY=http://127.0.0.1:3128" "NO_PROXY=localhost,127.0.0.1"
EOF
systemctl daemon-reload
systemctl enable --now docker
systemctl restart docker
docker version --format '{{.Server.Version}}'
docker pull ros:jazzy-ros-base-noble
docker image inspect ros:jazzy-ros-base-noble --format '{{json .RepoDigests}} {{.Architecture}}'
