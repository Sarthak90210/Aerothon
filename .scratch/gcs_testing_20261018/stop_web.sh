#!/usr/bin/env bash
for p in $(pgrep -f "aerothon_runtime.web --static"); do kill "$p"; done; sleep 2; pgrep -fa "aerothon_runtime.web --static" | grep -v pgrep || echo web-stopped
