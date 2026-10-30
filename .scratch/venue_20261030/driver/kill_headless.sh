#!/bin/bash
# Kill every headless-run process (all ROS domains), listing them first.
PAT='sim/headless_world.py|sim/record_delivery.py|sim/fly_headless.py|from sim.navigation_mission|from mission_bt.mission_tree|from avoidance.velocity_controller|from camera_ctrl.camera_ctrl_node|from winch_ctrl.winch_node|scripts/publish_delivery_zone.py|from gcs_aggregator.aggregator|scripts/gcs_operator.py|run_headless.sh'
for p in $(pgrep -f "$PAT"); do
  [ "$p" = "$$" ] && continue
  d=$(tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep '^ROS_DOMAIN_ID=')
  echo "$p $d up $(ps -o etimes= -p $p)s $(tr '\0' ' ' < /proc/$p/cmdline | cut -c1-80)"
done
pkill -9 -f "$PAT"
sleep 2
echo "left: $(pgrep -fc "$PAT")"
uptime
