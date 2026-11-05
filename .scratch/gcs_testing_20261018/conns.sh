#!/usr/bin/env bash
echo "video streams host->8080: $(ss -tn state established "( dport = :8080 )" | tail -n +2 | wc -l)"
