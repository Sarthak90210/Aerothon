#!/usr/bin/env bash
set -e
export GZ_PARTITION=aerothon_m2 GZ_IP=127.0.0.1
exec /usr/bin/python3 sim/record_contact_truth.py --out "$1/evaluation_contacts.jsonl" --until-file "$1/recorded_result.json"
