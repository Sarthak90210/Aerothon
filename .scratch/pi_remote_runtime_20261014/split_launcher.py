from pathlib import Path
p=Path('scripts/launch_level6_sim.sh');s=p.read_text()
a=s.index('echo "[1/5] Starting MAVLink Router');b=s.index('\necho "======================================================================"',a)
s=s[:a]+'''if [[ "${AEROTHON_LAPTOP_SERVICES_ONLY:-0}" == 1 ]]; then
    ros2 run aerothon_runtime laptop_gateway --fcu-udp "$FCU_IN_PORT" \\
      --port "${AEROTHON_GATEWAY_PORT:-8090}" --mavlink-port "${AEROTHON_GATEWAY_MAVLINK_PORT:-5762}" \\
      --camera-channel 9 --winch-channel 10 --winch-rate 1.0 &
    PIDS+=($!)
else
'''+s[a:b]+'''fi
'''+s[b:]
s=s.replace('    ros2 launch sim_gazebo sim_full.launch.py \\\n', '''    production=true
    mapping=true
    if [[ "${AEROTHON_LAPTOP_SERVICES_ONLY:-0}" == 1 ]]; then production=false; mapping=false; RVIZ_ARG=false; fi
    ros2 launch sim_gazebo sim_full.launch.py mission_stack:="$production" \\
''')
s=s.replace('rviz:="$RVIZ_ARG" slam:=true', 'rviz:="$RVIZ_ARG" slam:="$mapping"')
p.write_text(s)
