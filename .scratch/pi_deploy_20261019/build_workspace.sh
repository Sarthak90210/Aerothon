#!/usr/bin/env bash
set -u
stage=/home/pi5/aerothon-stage/20261019-slam-ui
workspace=/home/pi5/aerothon_ws
docker run --rm --pull=never --name aerothon-build-20261019 \
  --network none --user 1000:1000 --cap-drop ALL --security-opt no-new-privileges \
  --mount "type=bind,src=$workspace,dst=/workspace" \
  --mount "type=bind,src=$stage,dst=/deployment-stage,readonly" \
  aerothon-runtime:20261014 /bin/bash /deployment-stage/build_inside.sh > "$stage/build.log" 2>&1
result=$?
printf '%s\n' "$result" > "$stage/build_exit_code"
exit "$result"
