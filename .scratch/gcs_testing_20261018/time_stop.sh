#!/usr/bin/env bash
pid=$(pgrep -f "aerothon_runtime.web --static" | head -1)
start=$(date +%s.%N); kill "$pid"
while kill -0 "$pid" 2>/dev/null; do sleep 0.1; done
echo "web host exited $(echo "$(date +%s.%N) - $start" | bc) s after SIGTERM"
pgrep -f "mission2.launch.py" >/dev/null && echo "production runtime still running" || echo "production runtime gone"
