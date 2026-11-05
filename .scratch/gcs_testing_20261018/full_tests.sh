#!/usr/bin/env bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
out=logs/gcs_testing_20261018
mkdir -p "$out"
AEROTHON_OFFLINE_SCOPE_EVIDENCE="$out/offline_reduced_scope_2.json" \
  bash scripts/run_tests.sh --reduced-scope --quick > "$out/reduced_scope_quick_2.log" 2>&1
echo "exit $?" >> "$out/reduced_scope_quick_2.log"
