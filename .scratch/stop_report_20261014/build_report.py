"""Build the stopped-project report from preserved records, without flight execution."""
import hashlib
import html
import json
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REMOTE = ROOT / ".scratch/pi_remote_runtime_20261014"
LIVE = ROOT / "logs/pi_gateway_shipped_s20261003_onboardfix_20261014"

def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def text_of(path):
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")

baseline = read(".scratch/pi_remote_runtime_20261014/baseline.json")
changes = []
for name, before in baseline.items():
    path = ROOT / name
    after = sha(path) if path.is_file() else None
    if before != after:
        changes.append({"path": name, "before_sha256": before, "current_sha256": after})

with zipfile.ZipFile(REMOTE / "runtime7.zip") as bundle:
    manifest = json.loads(bundle.read("runtime_manifest.json"))
    manifest_files = manifest["files"]
    for name, expected in manifest_files.items():
        assert hashlib.sha256(bundle.read(name)).hexdigest() == expected, name
    mismatches = []
    for name, expected in manifest_files.items():
        path = ROOT / ("src/aerothon_gcs/tauri_app/dist/" + name[4:] if name.startswith("gcs/") else name)
        if not path.is_file() or sha(path) != expected:
            mismatches.append(name)

latest = read("logs/pi_gateway_shipped_s20261003_onboardfix_20261014/latest.json")
field = read("logs/pi_cleanup_hard_field_both_s20261004_retry1_20261013/summary.json")
clearance = read(".scratch/pi_consolidation_20261013/final_field_clearance_review.json")
merge = read(".scratch/gcs_merge_20261014/result.json")
refresh = read(".scratch/pi_refresh_20261014/result.json")
ledger = read(".scratch/pi_remote_runtime_20261014/offline-scope-4.json")
frames = [json.loads(line) for line in (LIVE / "camera_capture_events.jsonl").read_text().splitlines() if line.strip()]
assert "38 passed" in text_of(".scratch/pi_remote_runtime_20261014/focused4.log")
assert "1955 passed, 8 skipped" in text_of(".scratch/pi_remote_runtime_20261014/offline-4.log")
assert "OFFLINE CHECKS FAILED" in text_of(".scratch/pi_remote_runtime_20261014/offline-4.log")

original = [
 {"instruction":"Fix return-corridor recovery and meet 0.70 m clearance.","status":"Unresolved","done":"Several earlier navigation subsets passed. V44 completed three calm clarified-arena missions. The later combined-banner field mission completed delivery, return and disarm.","gap":"That field mission failed clearance at 0.663645 m, with 70 below-floor samples. No current Pi-source flight closes this obligation."},
 {"instruction":"Fix QR search, especially seed 2, and run seeds 1, 2 and 3 with normal timing and actuators.","status":"Incomplete","done":"Older object-level navigation records include passes for field seeds 1, 2 and 3. QR/camera/perception regressions and new capture transport checks passed.","gap":"Object-level navigation did not exercise rendered QR delivery. The latest Pi deployment has no completed seed 1, 2 or 3 mission proving QR search and return braking."},
 {"instruction":"Resolve strong gusts and artificially delayed control, later explicitly defer both.","status":"Deferred, unresolved","done":"Failures and the rejected wider lidar filter were preserved. Strong gusts and artificial control delay were excluded from the requested qualification scope.","gap":"These cases remain failures or unqualified. They cannot be counted as passes. Thin obstacles and acceptance thresholds were retained."},
 {"instruction":"Integrate the final controller, camera scheduling and perception with normal startup, then regress and run the full offline suite.","status":"Partly implemented","done":"Production planner, scan buffering, capture inbox and independent clock paths were retained. A managed Pi launch and remote sensor/actuator adapters were integrated. Focused tests and builds passed.","gap":"The latest complete offline attempt ended in a frontend TypeScript error after 1,955 Python passes. Focused checks passed after fixes, but no complete final-source offline pass exists."},
 {"instruction":"On one final source, pass standard seeds 20261003 and 1001, plus shipped, rotated and split rendered courses.","status":"Not completed","done":"Older V44 calm clarified-arena runs passed 22/22. Their source, configurations and evidence are preserved.","gap":"Those are a different matrix and source. None of the five requested rendered gates is qualified on the latest Pi bundle. Actual contact evidence, delivery and connected disarm are still required."},
 {"instruction":"Run the corrected campaign, later exclude strong gusts and delayed control and report the exact remaining case count.","status":"Not completed","done":"An older 96-flight reduced campaign plan is documented. Offline exclusions have an explicit ledger.","gap":"The final reduced world/seed/weather campaign has not been closed on the latest source. Its case list and exclusions need a final audit. Neither 96 qualified flights nor the original 200-case qualification is claimed."},
 {"instruction":"Consolidate accepted source, configurations, detector rates, recordings, telemetry, results and all remaining failures.","status":"Interim report complete; acceptance report pending","done":"Source bundles, run recordings, telemetry, configuration inputs, deployment receipts and failed attempts were retained. This report accounts for the stopped state.","gap":"There is no accepted final source. A final qualification report must wait for matching-source acceptance and campaign evidence."},
]

gcs_instructions = [
 "Replace the old GCS with the plain interface we designed, with Flight operations and Testing, neutral themes, readable text and thin dividers.",
 "Host the GCS and production algorithms on the Pi; run only Gazebo, SITL and a connection gateway on the laptop.",
 "Make profiles detailed and editable for changing addresses, FCU transports, identity, devices, sensor gateway, calibration and RC mappings. Keep DDS local to the Pi.",
 "Use the same production mission and component algorithms in both deployments, with one movement owner, explicit Start, recovery and transmitter takeover.",
 "Provide full mission, manual SLAM, transmitter and route avoidance, QR, banner, mechanism and position/GPS delivery tests.",
 "Restore map loading, all 20 production arena dimensions, flight/sensor graphs, vibration and magnetic indications, plus explicit stale/unavailable data.",
 "Initially allow a standalone receive-only telemetry GCS without algorithms; later merge it into the requested command-capable shared production runtime.",
 "Replace stale Pi code and services, preserve recovery copies and measured configuration, and work directly in main without new worktrees.",
 "Make green, orange and red banner colours operator-supplied hex codes, and apply them through the GCS to perception.",
 "At this stop, keep the report and project in the AEROTHON working folder, remove extra worktrees after preservation, and keep one maintained GCS.",
]

work = [
 {"area":"Plain GCS, map and arena","status":"Software delivered","proof":"Correct React interface restored; obsolete render.ts removed. Offline map assets, 20 arena fields and plain HTTP commands verified in the earlier merge and Pi refresh.","left":"Latest profile/task changes still need complete browser-to-flight verification. Cached imagery covers its bundled area, not arbitrary locations."},
 {"area":"Graphs and sensor indications","status":"Partly verified","proof":"Flight and sensor views, history, freshness gaps, selectable traces and CSV export exist. 25 frontend tests pass.","left":"The latest saved magnetic strength is 5.789e11 microtesla, an implausible value. Verify units/conversion before relying on it. Vibration Z is unavailable in that sample. No calibrated magnetic interference percentage is claimed."},
 {"area":"Pi software deployment and cleanup","status":"Software delivered","proof":"Latest bundle receipt verifies 255 files. ARM64 build finished 13 packages, including 12 local packages and the external lidar driver. Earlier cleanup freed about 1.77 GB and kept recovery archives.","left":"Latest live Pi status and boot/reconnect behaviour could not be checked at this stop because HTTP and SSH timed out."},
 {"area":"Laptop SITL/Gazebo to Pi connection","status":"Demonstrated while disarmed","proof":"Pi ran production ROS nodes and consumed actual rendered images, calibrated camera data, lidar and FCU telemetry from the laptop. FCU identity 1/1 and gateway session were checked.","left":"Changed-address profiles and duplicate receipts were observed, but dropped-link, pause, restart and recovery scenarios still need integrated operational trials."},
 {"area":"Shared supervisor and nine tasks","status":"Implemented, software tested","proof":"Nine task entrypoints construct using production components. Typed contracts, exclusive ownership, durable command IDs and lifecycle states exist; 38 focused runtime/native tests pass.","left":"Zero of the nine tasks has a completed Pi-to-laptop execution trial in this latest integration. Arming, takeoff, takeover, recovery and completion remain unverified together."},
 {"area":"Sensor timing and camera scheduling","status":"Implemented, passive observation verified","proof":"Capture timestamps retained; camera uses a newest-frame inbox on separate traffic; clock/lidar reader is independent. WebSocket heartbeat and camera backlog failures were corrected. Lidar rate uses capture-clock time plus a steady watchdog.","left":"No full mission proves detector throughput, freshness or congestion behaviour during flight. Production lidar and camera minimums were retained."},
 {"area":"Camera and winch compatibility","status":"Observation only","proof":"SITL PWM outputs and measured Gazebo joints gate capability checks. Passive readback reported camera FORWARD near 0.001 rad and winch payout near 0.000005 m.","left":"These values do not demonstrate commanded motion, release or delivery. Physical GPIO/encoder control is absent and unsupported hardware actuation is blocked."},
 {"area":"Dynamic green/orange/red hex colours","status":"Implemented, software and applied-input checks passed","proof":"All three #RRGGBB inputs are required. Banner and red-zone masks derive from them, including clipped-boundary evidence. 216 focused perception/configuration checks passed; applied colours appeared in Pi telemetry.","left":"No final rendered mission or physical photo set verifies the new path across lighting, backgrounds and all required courses."},
 {"area":"Final complete offline suite","status":"Incomplete","proof":"Earlier merge passed 1,927 tests with 8 skips. Latest broad attempt passed 1,955 Python tests with 8 skips and 9 native checks, then failed the frontend step. Later focused runtime/frontend/build checks passed.","left":"One complete final-source reduced suite, including frontend and configuration checks, remains outstanding. Overlapping focused counts must not be summed as unique tests."},
 {"area":"Rendered mission qualification","status":"Incomplete","proof":"Three older V44 calm clarified-arena missions passed 22/22. The later combined-banner field run completed and disarmed but failed 21/22.","left":"Seeds 1/2/3, the five requested rendered gates and actual Pi-managed full workflow are not closed on the latest source."},
 {"area":"Reduced campaign","status":"Pending","proof":"Historical source/configuration records and exclusions remain available. The original 200-case claim remains false.","left":"Freeze the final source, enumerate the final matrix and exclusions, run it after targeted gates, and record every outcome."},
 {"area":"Physical FCU, winch and power","status":"Hardware unqualified","proof":"Earlier physical telemetry worked through TELEM3 at 115200 on /dev/ttyAMA0. CPU power cap was recorded during earlier BEC diagnosis. Wiring records identify the camera servo and BTS7960/encoder plan.","left":"The UART was absent at the latest destination audit. GPIO/encoder winch implementation, loaded calibration, camera travel and BEC-only boot remain pending. USB-C boot does not qualify the BEC."},
]

failures = [
 {"name":"Original corridor and QR blockers","outcome":"Initial split return run passed only 17/22 with 0.687 m clearance; isolated seed 2 missed delivery after two QR search passes.","resolution":"Later navigation and calm mission subsets improved. Current-source rendered closure is still missing."},
 {"name":"Earlier V39 native contact evidence","outcome":"A focused native trial passed seven geometric checks but failed the independent contact-free assertion. The saved record includes armed skid/ground contacts.","resolution":"Preserved in the earlier stopped checkpoint. Geometry-only success was not promoted to full acceptance."},
 {"name":"Combined-banner field clearance","outcome":"21/22 checks. Minimum 0.663645 m against 0.70 m at return obstacle 0, native time 842.099 s. Seventy below-floor samples. Zero unexpected contacts, 0.11 m payload error, 886.1 s flight, actual disarm.","resolution":"Unresolved. The aircraft completed the mission, but the acceptance failure remains. The miss is about 3.64 cm."},
 {"name":"Operator-interrupted field run","outcome":"The next laid-only field trial was stopped in outbound banner alignment, then landed/disarmed with GRADE_FAIL and ABORTED_RTL.","resolution":"Retained as interrupted evidence. It is not a naturally completed mission or a claimed 900 s violation."},
 {"name":"Strong gusts and coupled artificial delay","outcome":"Obstacle-contact/return failures remain. A wider lidar filter was rejected because it could erase thin obstacles.","resolution":"Explicitly deferred and excluded. No obstacle removal or threshold relaxation was used."},
 {"name":"First Pi rendered connection","outcome":"FCU connected but sensor WebSockets closed; camera, lidar and clock became stale. No arm/start trial was run.","resolution":"Added the receiver loop needed for heartbeat replies. Original failed attempt retained."},
 {"name":"Second Pi rendered connection","outcome":"Camera processing queued frames, closed the stream and disrupted other channels. No flight was attempted.","resolution":"Changed transport scheduling to a newest-frame inbox and independent reader, with camera failure separated from clock/lidar."},
 {"name":"Third connection preflight","outcome":"QR health went silent while the camera was in a non-QR pose; lidar wall-clock rate looked below 8 Hz despite 10 Hz capture-clock input.","resolution":"QR reports NOT_VISIBLE health; lidar evaluates capture-clock rate and steady-time loss. Focused checks and disarmed readiness passed. Flight proof is still absent."},
 {"name":"Latest offline run","outcome":"After 1,955 passes and eight skips, Node rejected a TypeScript constructor parameter property in ApiError. The full command exited FAILED.","resolution":"Fixed the TypeScript syntax; 25 frontend checks and build passed afterward. Further readiness fixes mean a complete final suite is still required."},
 {"name":"Earlier banner performance run","outcome":"An earlier loaded merge trial failed the 100 ms/frame benchmark at about 214 ms/frame. A quiet full run passed afterward.","resolution":"Both records retained. The quiet pass does not establish worst-case detector throughput under Pi flight load."},
 {"name":"Development/deployment failures","outcome":"ROS import/test-runner and NumPy ABI conflicts, Windows/WSL file issues, reserved port 8090, WSL mirrored networking failure, Pi download failure, CRLF scripts, root-owned SQLite state and stale built asset references interrupted progress.","resolution":"Individual fixes and receipts exist. WSL now uses NAT with an explicit two-port relay. Reboot and integrated recovery verification remains incomplete."},
 {"name":"Telemetry and readiness inconsistencies","outcome":"Latest saved magnetic units are implausible. That same sample shows overall readiness true while the separate EKF display is UNKNOWN and stale markers remain.","resolution":"These are unresolved verification findings, not proof of a specific root cause. Reconcile units and readiness/display sources before treating the indication as reliable."},
 {"name":"Stop-time Pi access","outcome":"HTTP at 192.168.0.100:8899 and SSH at 192.168.0.100 timed out. No laptop simulator/relay/recorder was found active.","resolution":"Implementation stopped. Current Pi runtime and armed state cannot be certified remotely. Last recorded mission state was idle and disarmed; no mission Start or arm was sent during this integration."},
]

remaining = [
 {"item":"Restore Pi visibility and establish stopped state","proof":"Reach the new address, inspect fresh FCU/runtime state and receipts, and disconnect only after confirmed disarm. Verify one GCS service and no legacy controller process."},
 {"item":"Reconcile GCS telemetry and readiness","proof":"Verify magnetic units, vibration availability, EKF/fence freshness and agreement between capability/readiness/status views. Complete browser profile/task parameter and reviewed-Start checks."},
 {"item":"Close corridor, QR and return braking","proof":"Run normal-timing seeds 1, 2 and 3 without strong gusts or artificial delay. Diagnose observed failures and retain safe stopped attempts. Clearance must stay at least 0.70 m."},
 {"item":"Freeze and pass the final complete offline suite","proof":"Review the changed adapters/perception, freeze source and configuration, then complete the reduced suite, syntax/configuration and frontend checks once the final fixes are integrated."},
 {"item":"Execute all nine tasks through the Pi","proof":"Observe SLAM map/frame/origin/timestamp, QR, banner, manual/route avoidance, mechanism and delivery behaviours in laptop SITL/Gazebo. Prove movement ownership, transmitter takeover, recovery and duplicate-command handling."},
 {"item":"Verify connection and actuation failure behaviour","proof":"Exercise wrong identity, changed addresses, reconnects, stale sensors, simulation pause, dropped links, gateway restart and web/service restart. Prove actual camera/winch movement and release feedback, not only command acceptance."},
 {"item":"Complete the normal Pi-managed mission","proof":"Record the real rendered model workflow from Start through delivery, return, land and connected disarm, with source/configuration, native contacts and captured camera/telemetry."},
 {"item":"Pass all five requested rendered gates","proof":"On that same final source, pass standard seeds 20261003 and 1001 plus shipped, rotated and split courses. Keep 0.70 m corridor, 1.50 m restricted-zone clearance, 900 s limit, contact evidence, delivery and actual disarm."},
 {"item":"Close the reduced campaign and evidence report","proof":"Audit the exact final world/seed/weather case count and exclusions, run the remaining matrix after targeted passes, retain every outcome and state accepted_source only when acceptance is actually achieved."},
 {"item":"Complete physical hardware separately","proof":"Restore/verify the single-owner FCU UART; implement and measure Pi 5 GPIO/encoder winch control; calibrate camera travel, payload retention and loaded/unloaded delivery; prove BEC-only boot. Simulation passes do not close these hardware obligations."},
]

evidence = [
 ("Operating guide and qualification ledger", "MASTER_DOCUMENTATION.md"),
 ("Preserved Phase 2 flight evidence", "logs/archived_phase2_20261014"),
 ("Earlier stopped V39 checkpoint", ".scratch/simulation-reliability/handoff_stop_checkpoint_20261010.json"),
 ("V44 source provenance", "logs/reliability_reduced_scope_v44_source_20261013/provenance.json"),
 ("Failed field mission summary", "logs/pi_cleanup_hard_field_both_s20261004_retry1_20261013/summary.json"),
 ("Field clearance review", ".scratch/pi_consolidation_20261013/final_field_clearance_review.json"),
 ("Field overview video with actual FAIL", "logs/pi_cleanup_hard_field_both_s20261004_retry1_20261013/overview/world_overview.mp4"),
 ("GCS merge report", ".scratch/gcs_merge_20261014/result.json"),
 ("Pi refresh and cleanup report", ".scratch/pi_refresh_20261014/result.json"),
 ("Latest immutable runtime bundle", ".scratch/pi_remote_runtime_20261014/runtime7.zip"),
 ("Latest destination bundle receipt", ".scratch/pi_remote_runtime_20261014/runtime7-install.log"),
 ("38 focused runtime/native passes", ".scratch/pi_remote_runtime_20261014/focused4.log"),
 ("216 focused colour/perception passes", ".scratch/pi_remote_runtime_20261014/colours-focused1.log"),
 ("Latest broad offline failure", ".scratch/pi_remote_runtime_20261014/offline-4.log"),
 ("Offline exclusion ledger", ".scratch/pi_remote_runtime_20261014/offline-scope-4.json"),
 ("25 frontend passes", ".scratch/pi_remote_runtime_20261014/frontend-final-tests.log"),
 ("Latest frontend build", ".scratch/pi_remote_runtime_20261014/frontend-final3-build.log"),
 ("Latest disarmed Pi telemetry", "logs/pi_gateway_shipped_s20261003_onboardfix_20261014/latest.json"),
 ("Recorded Pi telemetry stream", "logs/pi_gateway_shipped_s20261003_onboardfix_20261014/telemetry.jsonl"),
 ("Rendered input capture timeline", "logs/pi_gateway_shipped_s20261003_onboardfix_20261014/camera_capture_events.jsonl"),
 ("Rendered input frames", "logs/pi_gateway_shipped_s20261003_onboardfix_20261014/camera_frames"),
 ("Saved laptop connection profile", ".scratch/pi_remote_runtime_20261014/laptop-profile.json"),
 ("Operator dimensions", "logs/pi_gateway_shipped_s20261003_onboardfix_20261014/operator_dimensions.json"),
 ("Operator boundaries", "logs/pi_gateway_shipped_s20261003_onboardfix_20261014/operator_boundaries.json"),
 ("Archived previous Pi installation", ".scratch/pi_deploy_20261014/previous_pi_installation.tar.gz"),
 ("Archived pre-refresh runtime", ".scratch/pi_refresh_20261014/previous_current_runtime.tar.gz"),
]

method = [
 ("Traceable conclusions", "Claim licences", 8, 6, 8, "Jargon could obscure a plain report."),
 ("Traceable conclusions", "Instruction-to-flight proof chains", 8, 9, 10, "Selected"),
 ("Separate source versions", "Evidence grouped by source and configuration", 8, 9, 10, "Same underlying idea as source-version groups."),
 ("Traceable conclusions", "Challenge cards for completion claims", 7, 7, 8, "Uniform cards conflict with the requested plain layout."),
 ("Operational closure", "Operator handover by next action", 7, 8, 8, ""),
 ("Traceable conclusions", "Readiness claims with receipts", 7, 8, 9, ""),
 ("Operational closure", "Failure-response map by symptom", 8, 7, 8, ""),
 ("Operational closure", "Remaining obligations with exact acceptance evidence", 8, 9, 10, "Selected"),
 ("Traceable conclusions", "One evidence receipt for every promise", 7, 9, 10, ""),
 ("Operational closure", "Mission path with proven gates", 7, 8, 9, ""),
 ("Separate source versions", "Source-version evidence groups", 8, 9, 10, "Selected"),
 ("Operational closure", "Expected versus observed failure pairs", 7, 9, 10, ""),
]

worktrees = subprocess.check_output(["git", "worktree", "list", "--porcelain"], cwd=ROOT, text=True)
consolidation_file = ROOT / ".scratch/worktree_consolidation_20261014/result.json"
consolidation = json.loads(consolidation_file.read_text()) if consolidation_file.exists() else {"status":"preservation/removal still in progress"}
if consolidation_file.exists():
    evidence.append(("Worktree preservation and removal receipt", ".scratch/worktree_consolidation_20261014/result.json"))

stats = [
 ["Earlier V44 calm clarified-arena flights", "3 passed 22/22", "Earlier source; separate from current Pi qualification"],
 ["Earlier V44 headless navigation", "16 passed", "Rendered perception and physical delivery not qualified"],
 ["Latest runtime task registry", "9 entrypoints", "Software construction checked; 0 completed Pi execution trials"],
 ["Latest Pi-managed full missions", "0 completed", "Only disarmed connection/preflight observations"],
 ["Latest requested rendered gates", "0 of 5 qualified", "No current-source acceptance claim"],
 ["Latest native/runtime focused checks", "38 passed", "Focused software tests, not flight acceptance"],
 ["Latest colour/perception checks", "216 passed", "Focused and overlapping with other reported subsets"],
 ["Latest frontend checks", "25 passed", "Build passed; full final suite still missing"],
 ["Latest broad Python attempt", "1,955 passed; 8 skipped", "Whole offline command FAILED at frontend"],
 ["Latest verified Pi package", "255 files; 13 ARM packages", "Software installation; not hardware qualification"],
 ["Archived latest rendered input", f"{len(frames):,} JPEG captures", "Passive pre-arm session; not a mission acceptance video"],
]

report = {
 "schema":"aerothon-stopped-project-report/1", "client_date":"2026-10-14", "timezone":"Asia/Calcutta",
 "status":"stopped_by_user", "accepted_source":False, "flight_qualified":False, "original_200_case_qualified":False,
 "summary":"The plain GCS and much of the Pi/laptop runtime were implemented and software-tested. I did not complete the requested final flight qualification, campaign or physical integration. The latest Pi connection reached disarmed preflight observation, not a completed mission.",
 "accountability":"I spent substantial effort fixing GCS migration, Pi deployment and network/sensor integration. I did not carry that work through the required final complete suite and matching-source flights. Working screens, Accepted receipts and green focused tests are insufficient to call the whole system ready. I am not assigning a completion percentage because software items and flight qualification gates are different obligations.",
 "stop_state":"No AeroTHON simulator, gateway relay or camera/telemetry recorder was found active on the laptop at the stop check. Pi HTTP and SSH at 192.168.0.100 timed out, so its current process and armed state could not be confirmed. Last saved Pi telemetry was idle, STABILIZE and disarmed. No mission Start or arm command was sent during the latest Pi integration. No further feature work or qualification run was started to write this report.",
 "original_instructions":original, "gcs_instructions":gcs_instructions, "completion":work, "failures":failures,
 "remaining":remaining, "statistics":stats,
 "source":{"branch":"main", "git_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
   "dirty_worktree":True, "bundle":".scratch/pi_remote_runtime_20261014/runtime7.zip", "bundle_sha256":sha(REMOTE/"runtime7.zip"),
   "frozen_copy_sha256":sha(LIVE/"frozen_pi_runtime.zip"), "verified_payload_files":len(manifest_files), "current_payload_mismatches":mismatches,
   "image_id":"sha256:3b17f1eacc92891c3badb318c1a29bd7df6af4b53fb969771ead7bae5c47e51d",
   "image_tag":"aerothon-runtime:20261014-network", "changed_baseline_files":changes,
   "flight_code_scope":"The earlier GCS merge and Pi refresh kept flight decisions unchanged. The later shared-runtime work changed launch/readiness, the velocity-controller external-intent adapter, camera and winch feedback handling, QR health reporting, and banner/red-zone colour perception. The existing mission tree and fast planner were retained relative to the latest integration baseline. These flight-facing changes need new flight evidence. This was more than a GCS-only migration."},
 "configuration":{"pi_address":"192.168.0.100, last requested; unreachable at stop-time check", "laptop_lan":"192.168.0.102", "wsl_nat":"172.26.219.3", "fcu_tcp_port":5762,"sensor_http_port":19090,"identity":"system 1, component 1", "profile":read(".scratch/pi_remote_runtime_20261014/laptop-profile.json"), "banner_hex":{"green":"#07A03D","orange":"#EB5A0A","red":"#C4161C"},"dds_domains":{"pi":42,"laptop":43},"timing":"Normal control/actuator behaviour; no artificially injected command delay. Strong gusts excluded."},
 "rates":{"scope":"One saved disarmed snapshot, not mission-wide detector throughput", "camera":latest["devices"]["camera"],"lidar":latest["devices"]["lidar"],"historical_failed_field_detector_rates":field.get("detector_rates"),"actual_qr_banner_red_processing_rates_for_current_full_mission":"Not measured; no current full mission"},
 "recording":{"jpeg_count":len(frames),"first_capture_stamp":frames[0]["capture_stamp"],"last_capture_stamp":frames[-1]["capture_stamp"],"basis":"Original rendered camera capture stamps; camera_optical_frame; not fabricated or restamped"},
 "offline_exclusions":{"collected_tests":ledger["collected_tests"],"included_tests":ledger["included_test_count"],"excluded_tests":ledger["excluded_tests"],"missing_photo_skips":3,"flight_campaign_count":"Historical reduced plan 96; final current-source case list and completed count not established"},
 "worktrees_at_report":worktrees,"consolidation":consolidation,
 "one_gcs":{"source":"src/aerothon_gcs/tauri_app", "server":"src/aerothon_runtime/aerothon_runtime/web.py", "launcher":"scripts/serve_gcs.sh and the Pi aerothon-gcs service call that same web host", "aggregator":"ROS telemetry/perception adapter within the same GCS, not a separate frontend", "old_frontend":"render.ts removed; old standalone source absent from main", "remote_service_status":"Previous destination receipts configured one GCS and disabled the old console; cannot reverify current Pi services while unreachable"},
 "evidence":[{"label":label,"path":path,"exists":(ROOT/path).exists()} for label,path in evidence],
 "historical_memory_note":"The earlier standalone deployment, real FCU stream diagnosis, laptop forwarding and BEC power history come from the 8 October saved rollout. They were not reverified live for this report and may be outdated. Current qualification and recent deployment counts come from the actual working-folder receipts.",
 "report_method":{"frames":["regulator","3am on-call","curious 10-year-old"],"candidates":[{"cluster":c,"idea":i,"novelty":n,"viability":v,"fit":f,"weighted_score":round(n*.35+v*.4+f*.25,2),"note":s} for c,i,n,v,f,s in method],"selected":["Instruction-to-flight proof chains","Source-version evidence groups","Remaining obligations with exact acceptance evidence"],"wildcard":"Make a source freeze the unit of qualification."},
}
(OUT/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")

e = lambda s: html.escape(str(s), quote=True)
def table(headers, rows):
    return '<div class="table-scroll"><table><thead><tr>'+''.join('<th>'+e(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+e(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'

parts = ["<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>AeroTHON stopped-project report</title><style>body{font:15px/1.6 system-ui,sans-serif;color:#202020;background:#fafafa;margin:0}main{max-width:1100px;margin:auto;padding:34px 26px 80px}h1{font-size:24px;margin:0 0 6px}h2{font-size:19px;margin:32px 0 10px}h3{font-size:16px;margin:20px 0 5px}p{margin:8px 0 14px}.meta,small{color:#525252;font-size:13px}.lead{font-size:18px;line-height:1.5;max-width:900px}.line{border-top:1px solid #d3d3d3;padding-top:18px}.table-scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;line-height:1.5}th,td{text-align:left;vertical-align:top;padding:10px 12px 10px 0;border-bottom:1px solid #ddd}th{font-weight:600}td:first-child{min-width:145px}ol,ul{padding-left:22px}li{margin:8px 0}a{color:#202020;text-decoration:underline;text-underline-offset:3px}code{font:12px/1.5 ui-monospace,monospace;overflow-wrap:anywhere}details{border-top:1px solid #d3d3d3;padding:12px 0}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}nav a{margin-right:16px;display:inline-block}.hash{overflow-wrap:anywhere}@media print{body{background:white}main{padding:0;font-size:11px}h2{break-after:avoid}tr{break-inside:avoid}.meta{font-size:10px}nav{display:none}details{display:block}}</style><main>"]
parts += ["<h1>AeroTHON stopped-project report</h1>","<p class='meta'>14 October 2026 · Asia/Calcutta · Main working folder · Work stopped by user</p>","<p class='lead'>"+e(report["summary"])+"</p>","<p>"+e(report["accountability"])+"</p>","<nav><a href='#instructions'>Instructions</a><a href='#completion'>Completed work</a><a href='#failures'>Failures</a><a href='#remaining'>Remaining work</a><a href='#evidence'>Evidence</a></nav>","<p class='line'>"+e(report["stop_state"])+"</p>","<h2>How much was actually proved</h2>",table(["Obligation or check","Recorded amount","Scope"],stats)]
parts += ["<h2 id='instructions'>What you originally instructed me to do</h2>","<p>The work began with flight reliability and qualification. You later deferred strong gusts and artificial control delay, while retaining normal actuator behaviour and every acceptance threshold.</p>"]
for n,item in enumerate(original,1):
    parts += [f"<h3>{n}. {e(item['instruction'])}</h3>","<p><strong>"+e(item["status"])+".</strong> "+e(item["done"])+"</p>","<p>"+e(item["gap"])+"</p>"]
parts += ["<h2>How the GCS and deployment scope expanded</h2>","<p>While simulation work was underway, you asked for the GCS redesign, then standalone Pi operation, physical telemetry routing, a merged production interface, full Pi deployment and the shared laptop simulation runtime. These were authorised additions. They did not remove the unfinished flight acceptance obligations.</p>","<ol>"+''.join('<li>'+e(x)+'</li>' for x in gcs_instructions)+"</ol>","<p>In the earlier standalone deployment, the GCS was deliberately receive-only. The later requested merged runtime is command-capable. These are different stages of your requested system. The old standalone interface is not the maintained GCS now.</p>","<h2 id='completion'>What exists and what has been verified</h2>",table(["Work","Status","Demonstrated evidence","Still missing"],[[x['area'],x['status'],x['proof'],x['left']] for x in work])]
parts += ["<h2>Was flight-related code changed?</h2>","<p>"+e(report["source"]["flight_code_scope"])+"</p>","<p>I also changed deployment services and the laptop network setup. Earlier power diagnosis applied a reversible Pi CPU cap. Those infrastructure changes are distinct from mission decisions. No BEC-only power qualification was completed.</p>","<h2 id='failures'>What failed, and what I did not finish</h2>"]
for x in failures:
    parts += ["<h3>"+e(x['name'])+"</h3>","<p>"+e(x['outcome'])+"</p>","<p>"+e(x['resolution'])+"</p>"]
parts += ["<h2>Timing, recordings and exclusions</h2>","<p>The latest saved disarmed snapshot reports camera input at "+e(round(latest['devices']['camera']['vehicle_hz'],2))+" captures/s of vehicle time and "+e(latest['devices']['camera']['hz'])+" receipts/s of wall time, with capture age "+e(latest['devices']['camera']['capture_age_s'])+" s. Lidar is about 10 captures/s of vehicle time and "+e(latest['devices']['lidar']['hz'])+" receipts/s of wall time, with capture age "+e(latest['devices']['lidar']['capture_age_s'])+" s. The distinct time bases reflect the rendered simulator running below real time. These are input rates, not successful detection rates.</p>","<p>The archived passive session contains "+e(f'{len(frames):,}')+" actual JPEG captures with original capture timestamps. It has telemetry and operator input files, but no completed mission or through-flight disarm video. Current full-mission QR, banner and red-zone processing rates were not measured.</p>","<p>The older failed combined-banner field run measured QR search throughput at about 17.20 captures/s of simulated time and 4.51/s of wall time; red-zone throughput was about 17.21/s of simulated time and 4.52/s of wall time. Those rates belong to that older failed flight source.</p>","<p>The latest offline ledger collected 1,963 tests. Five strong-gust test nodes were explicitly excluded, and three real-photo corpus checks skipped because their inputs were absent. All eight remain skips. The five fixtures use mean wind 8 m/s and gust 4 m/s. Artificially delayed-control flight cases also remain outside qualification. This ledger is a software-test count, not a flight-campaign count.</p>","<h2 id='remaining'>What remains before completion can be claimed</h2>","<p>These are outstanding obligations recorded at the stop. I have not resumed their execution.</p>","<ol>"+''.join('<li><strong>'+e(x['item'])+'.</strong> '+e(x['proof'])+'</li>' for x in remaining)+"</ol>"]
parts += ["<h2>Working folder and one GCS</h2>","<p>"+e('Worktree consolidation status: '+report['consolidation']['status'])+". Unique source and historical flight evidence are preserved inside this AEROTHON folder. Recovery ZIPs and Git history are archives, not additional maintained GCS installations.</p>","<pre>"+e(worktrees)+"</pre>","<p>The maintained browser source is <code>src/aerothon_gcs/tauri_app</code>. Its server is <code>src/aerothon_runtime/aerothon_runtime/web.py</code>. <code>scripts/serve_gcs.sh</code> and the Pi GCS service invoke that same server. The ROS aggregator supplies its telemetry and perception data. The deleted <code>render.ts</code> and former standalone source are not alternative maintained frontends.</p>","<p>Previous destination receipts show one configured GCS and the old console disabled. I cannot certify the Pi's current services while it is unreachable.</p>","<h2 id='evidence'>Source and configuration identity</h2>","<p>Git branch <code>main</code>, HEAD <code>"+e(report['source']['git_head'])+"</code>, dirty working tree. Git HEAD alone does not identify the deployed code.</p>","<p>Latest verified destination bundle <code>runtime7.zip</code>, SHA256 <code class='hash'>"+report['source']['bundle_sha256']+"</code>. The recorded run's frozen copy has the same hash. It contains "+e(len(manifest_files))+" verified payload files. Current local payload mismatches against that bundle: "+e(len(mismatches))+".</p>","<p>Pi image <code>"+e(report['source']['image_tag'])+"</code>, ID <code class='hash'>"+e(report['source']['image_id'])+"</code>. This is the last verified deployment identity, not a newly observed live Pi state.</p>","<p>Saved laptop endpoint <code>192.168.0.102:5762</code>, sensor gateway <code>http://192.168.0.102:19090</code>, WSL NAT target <code>172.26.219.3</code>, system/component <code>1/1</code>, Pi/laptop DDS domains <code>42/43</code>. The Pi initiates the connection. Green <code>#07A03D</code>, orange <code>#EB5A0A</code>, red <code>#C4161C</code> were applied through the operator path. No strong gusts or artificial command delay were injected in the latest connection attempts.</p>","<ul>"+''.join('<li><a href="'+quote('../../'+x['path'],safe='/')+'">'+e(x['label'])+'</a><small> · '+e(x['path'])+'</small></li>' for x in report['evidence'] if x['exists'])+"</ul>","<p class='meta'>"+e(report['historical_memory_note'])+" All acceptance failures and interrupted attempts remain attached to their own source/configuration. Older successes were not combined into latest-source qualification.</p>"]
parts += ["<details><summary>Report method requested through the ADHD skill</summary><p>I used three independent report-only frames because three agent slots were available. They generated 12 structures. I selected proof chains, source-version groups and explicit remaining acceptance obligations. No agent changed flight code or ran a trial.</p>",table(["Cluster","Candidate","Novelty / viability / fit","Weighted score","Decision"],[[x['cluster'],x['idea'],f"{x['novelty']} / {x['viability']} / {x['fit']}",x['weighted_score'],x['note']] for x in report['report_method']['candidates']]),"<p>The weighting was novelty 0.35, viability 0.40 and fit 0.25. Scores concern report organisation, not engineering completion.</p><h3>Selected approach</h3><p>Each requirement ends at its last demonstrated evidence link. Results remain grouped by source and configuration. Remaining work names an observable completion condition. The shared risk is accidentally treating an older pass, a software test or a disarmed connection as full mission acceptance.</p><h3>What these approaches add</h3><p>Proof chains attach each instruction to code, checks, observation and flight evidence. Source groups keep historical V44 flights separate from the current Pi bundle. Remaining obligations identify the decisive test and evidence needed for closure. The first report-writing step was extracting original obligations and attaching existing receipts before assigning status.</p><p>Useful variations are per-claim evidence links, measured failure-versus-threshold records, source/configuration stamps, and explicit missing-proof statements. Traps rejected were jargon-heavy claims, decorative repeated cards, invented completion percentages and treating Accepted commands as physical outcomes.</p><p>Further perspective: make a source freeze the unit of qualification.</p></details></main></html>"]
(OUT/"AEROTHON-status-report.html").write_text('\n'.join(parts),encoding="utf-8")

canvas_data = {k:report[k] for k in ('summary','accountability','stop_state','original_instructions','gcs_instructions','completion','failures','remaining','statistics','source','configuration','evidence','consolidation','one_gcs')}
canvas = '''import { Button, Code, Divider, H1, H2, H3, Row, Stack, Table, Text, useCanvasAction, useCanvasState, useHostTheme } from "cursor/canvas";
const ROOT = __ROOT__;
const DATA = __DATA__;
export default function AeroTHONStatusReport() {
 const theme = useHostTheme();
 const open = useCanvasAction();
 const [section, setSection] = useCanvasState<string>("aerothon-stop-section", "overview");
 const sections = ["overview", "instructions", "failures", "remaining", "evidence"];
 return <Stack gap={16} style={{ maxWidth: 1160, margin: "0 auto", padding: 24, color: theme.text.primary }}>
  <H1>AeroTHON stopped-project report</H1>
  <Text tone="secondary">14 October 2026 · Main working folder · Work stopped by user</Text>
  <Text weight="medium">{DATA.summary}</Text>
  <Row wrap>{sections.map(s => <Button key={s} variant={s===section ? "primary" : "ghost"} onClick={() => setSection(s)}>{s[0].toUpperCase()+s.slice(1)}</Button>)}</Row>
  <Divider />
  {section==="overview" && <Stack gap={14}>
   <Text>{DATA.accountability}</Text><Text>{DATA.stop_state}</Text>
   <H2>How much was actually proved</H2>
   <Table framed={false} headers={["Check", "Recorded amount", "Scope"]} rows={DATA.statistics}/>
   <H2>What exists and what remains</H2>
   <Table framed={false} headers={["Work", "Status", "Demonstrated", "Missing"]} rows={DATA.completion.map(x => [x.area,x.status,x.proof,x.left])}/>
   <H2>Flight-related code changes</H2><Text>{DATA.source.flight_code_scope}</Text>
   <H2>Working folder and one GCS</H2><Text>{DATA.consolidation.status}</Text>
   <Text>The maintained source is <Code>{DATA.one_gcs.source}</Code>, served by <Code>{DATA.one_gcs.server}</Code>. Historical source is archived for recovery.</Text>
  </Stack>}
  {section==="instructions" && <Stack gap={16}>
   <H2>Original flight obligations</H2>
   {DATA.original_instructions.map((x,i) => <Stack key={x.instruction} gap={6}><H3>{i+1}. {x.instruction}</H3><Text weight="semibold">{x.status}</Text><Text>{x.done}</Text><Text>{x.gap}</Text><Divider /></Stack>)}
   <H2>GCS and deployment instructions</H2>{DATA.gcs_instructions.map((x,i) => <Text key={x}>{i+1}. {x}</Text>)}
  </Stack>}
  {section==="failures" && <Stack gap={16}><H2>Recorded failures and incomplete work</H2>{DATA.failures.map(x => <Stack key={x.name} gap={6}><H3>{x.name}</H3><Text>{x.outcome}</Text><Text>{x.resolution}</Text><Divider /></Stack>)}</Stack>}
  {section==="remaining" && <Stack gap={16}><H2>Remaining proof before completion</H2><Text>These are recorded obligations. Their execution remains stopped.</Text>{DATA.remaining.map((x,i) => <Stack key={x.item} gap={6}><H3>{i+1}. {x.item}</H3><Text>{x.proof}</Text><Divider /></Stack>)}</Stack>}
  {section==="evidence" && <Stack gap={16}>
   <H2>Source identity</H2><Text>Dirty main checkout, Git HEAD <Code>{DATA.source.git_head}</Code>.</Text>
   <Text>Last verified destination bundle SHA256 <Code>{DATA.source.bundle_sha256}</Code>.</Text>
   <Text>Image <Code>{DATA.source.image_tag}</Code>. No current-source accepted mission.</Text>
   <Text>{DATA.source.verified_payload_files} verified bundle files, {DATA.source.current_payload_mismatches.length} current local payload mismatches.</Text>
   <H2>Evidence files</H2>{DATA.evidence.filter(x=>x.exists).map(x => <Row key={x.path} gap={12} wrap><Button variant="ghost" onClick={() => open({type:"openFile",path:ROOT+"/"+x.path})}>{x.label}</Button><Text size="small" tone="secondary">{x.path}</Text></Row>)}
  </Stack>}
 </Stack>;
}
'''.replace('__ROOT__',json.dumps(str(ROOT).replace('\\','/'))).replace('__DATA__',json.dumps(canvas_data,ensure_ascii=True))
(OUT/"AEROTHON-status-report.canvas.tsx").write_text(canvas,encoding="utf-8")
sdk = "C:/Users/sarth/.cursor/skills-cursor/canvas/sdk/index.d.ts"
types = str(ROOT/"src/aerothon_gcs/tauri_app/node_modules/@types/react").replace('\\','/')
tsconfig={"compilerOptions":{"target":"ES2021","module":"ESNext","moduleResolution":"bundler","jsx":"react-jsx","strict":True,"noEmit":True,"skipLibCheck":True,"lib":["ESNext","DOM"],"baseUrl":".","paths":{"cursor/canvas":[sdk],"react":[types+"/index.d.ts"],"react/jsx-runtime":[types+"/jsx-runtime.d.ts"]}},"include":["AEROTHON-status-report.canvas.tsx"]}
(OUT/"tsconfig.json").write_text(json.dumps(tsconfig,indent=2),encoding="utf-8")
print(json.dumps({"report":str(OUT/"AEROTHON-status-report.html"),"canvas":str(OUT/"AEROTHON-status-report.canvas.tsx"),"bundle_sha256":report['source']['bundle_sha256'],"payload_mismatches":mismatches,"baseline_changed_files":len(changes),"jpeg_captures":len(frames),"evidence_links":len(evidence),"worktree_status":consolidation['status']},indent=2))
