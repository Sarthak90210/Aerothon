from pathlib import Path
p=Path('MASTER_DOCUMENTATION.md');s=p.read_text()
a=s.index('The maintained browser GCS uses');b=s.index('\nGraphs retain ten minutes',a)
s=s[:a]+'''The browser GCS uses the same plain workspace for Flight operations and
Testing. Camera, SLAM, Map and Graphs share the persistent status strip,
task controls, readiness, event log and connection settings. Tests select
`mission`, `slam`, `qr`, `banner`, `avoidance_manual`, `avoidance_route`,
`mechanism`, `delivery_here` or `delivery_gps`. The supervisor uses the current
production tree and components. QR and SLAM observation do not arm. Mechanism
bench tests require disarm and measured actuator capability. Flight tests
use one reviewed Start, then production return/land on completion or Stop.
Transmitter takeover releases command ownership without a competing mode request.

Open `http://<pi-address>:8899/`. Browser API, WebSocket `/ws`, video and map
requests use the same origin. Connections saves vehicle profiles on the Pi:
FCU TCP/UDP/UART, hostname, ports, system/component identity, remote sensor
gateway, local devices, calibration and RC mappings. Save only with runtime
stopped and aircraft disarmed. Connect prepares sensors and the supervisor;
it does not arm, start a mission or move the camera. A profile with SLAM enabled
starts production mapping; the GCS displays its frame, origin and timestamp.
Camera view tabs do not move the camera; explicit camera tilt is reviewed.

For laptop simulation, run `bash scripts/launch_laptop_sim.sh` in the built
Ubuntu/Jazzy workspace. It reuses the current vehicle/world launcher with
`mission_stack:=false`: Gazebo, SITL, device bridges and gateway run on the
laptop; production perception, avoidance and execution run only on the Pi.
The gateway needs `pymavlink` in a Python environment compatible with the
system ROS/cv_bridge NumPy. TCP port 5762 carries FCU commands/telemetry; HTTP
port 8090 carries the manifest and separate camera/sensor WebSockets. Configure
the laptop hostname/IP and `http://<laptop>:8090` in the Pi profile. With WSL
NAT, expose those TCP ports on the laptop intranet address to WSL; configure
the profile with the exposed address. DDS stays local (Pi domain 42, laptop 43).
The gateway receives actual SITL actuator PWM and measured model joints;
world layout, grading, contacts and payload attachment state stay on the laptop.
Connection check reports identity, camera/calibration, lidar, clock and each
actuator independently. Wrong identities, stale captures, paused/backward
clock and unsupported actuators block affected executions. Gateway restarts
require explicit disconnect/reconnect. Watchdogs use steady time.

Arena fields use the production schema and remain editable offline as a draft.
Aircraft application requires live disarm; command receipt and applied
confirmation differ. Cached satellite coverage does not invent an aircraft GPS.
'''+s[b:]
a=s.index('Commands carry unique IDs');b=s.index('\nThe arena inclusion fence',a)
s=s[:a]+'''Commands use durable IDs stored before dispatch in the Pi SQLite receipt
ledger. Reconnects and duplicate requests do not repeat arming or release.
Submitted, Accepted, Running, Completed, Failed and Outcome unknown are distinct.
An Accepted receipt is not proof of motion, release, delivery or disarm. After
an unknown outcome, inspect fresh evidence before another start. Recovery
remains available when readiness fails. One supervisor owns movement; new
starts cannot replace active executions. Hardware camera/winch motion and
physical delivery remain unqualified; the GPIO/encoder winch is not implemented.
'''+s[b:]
a=s.index('`aerothon-gcs.service` serves');b=s.index('\nAt inspection, the old standalone',a)
s=s[:a]+'''`aerothon-gcs.service` runs the Pi web host inside the Jazzy container.
It starts at boot with no vehicle execution. `aerothon-router.service` watches
the explicitly selected hardware profile and is the single UART owner.
Network profiles use MAVROS directly through their configured TCP/UDP endpoint;
they do not open the physical UART. The former console service is disabled,
and direct mission-service launch refuses to create a second controller.

The web process is supervised inside a persistent container. A web-process
restart can adopt its existing ROS child by boot/PID identity. Service shutdown
first requests safe runtime disconnect; it refuses termination of a controlled
runtime without live disarm. The Docker attach process uses `--sig-proxy=false`
so a refused stop does not forward a kill to the flight container. Power loss
and FCU failsafe remain separate hardware concerns.

Open `http://192.168.0.101:8899/`, select Connections, save a profile, Connect
vehicle and run Connection check. For hardware, use the measured TELEM3
`/dev/ttyAMA0` at 115200 and review secured props-off wiring first. At the last
inspection this device was absent. `/dev/serial0` is the debug/login UART.
For laptop simulation, use its gateway endpoints instead. Supply organiser
arena dimensions, inclusion fence, delivery boundary and banner colours through
the GCS, inspect readiness, then Review start and Confirm Start.
'''+s[b:]
p.write_text(s)
