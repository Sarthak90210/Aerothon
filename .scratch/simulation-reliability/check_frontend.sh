#!/usr/bin/env bash
set -e
export PATH="/home/sarthak/.nvm/versions/node/v24.18.0/bin:/usr/bin:/bin:$PATH"
cd src/aerothon_gcs/tauri_app
node --version
node node_modules/typescript/bin/tsc --noEmit
node node_modules/vite/bin/vite.js build
