#!/usr/bin/env bash
for p in $(pgrep -f 'gcs_testing_20261018/(fake_vehicle|run_web)\.py|gcs_aggregator\.aggregator|web_video_server|slam_toolbox|lifecycle_manager'); do kill -9 "$p"; done
pkill -x sleep; pkill -f run_stack.sh; true
