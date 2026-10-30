#!/bin/bash
# Read-only: the Pi 5's input voltage and throttle flags 5x a second for
# 20 min, each line synced to disk so a brownout reset leaves the last ones.
out=/home/pi5/.local/state/aerothon/deploy_20261027b/volt_$(date +%Y%m%dT%H%M%S).log
echo "boot $(uptime -s)" >> "$out"
end=$((SECONDS + 1200))
while (( SECONDS < end )); do
    v=$(vcgencmd pmic_read_adc EXT5V_V | sed 's/.*=//')
    t=$(vcgencmd get_throttled | sed 's/.*=//')
    echo "$(date +%T.%N | cut -c1-12) $v $t" >> "$out"
    sync "$out"
    sleep 0.2
done
