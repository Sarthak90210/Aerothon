#!/usr/bin/env bash
set -eo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/src/aerothon_gcs/tauri_app'
node_runtime=/home/sarthak/.nvm/versions/node/v24.18.0/bin/node
"$node_runtime" --version
"$node_runtime" node_modules/typescript/bin/tsc --noEmit
"$node_runtime" node_modules/vite/bin/vite.js build
echo FRONTEND_BUILD_PASS
