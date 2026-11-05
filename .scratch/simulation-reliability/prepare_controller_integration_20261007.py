"""Stage the proven scheduling changes with optional diagnostic startup."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
base = root/'.scratch/capture_inbox_candidate_20261007/src/aerothon_avoidance/avoidance/avoidance'
out = root/'.scratch/controller_integration_20261007/src/aerothon_avoidance/avoidance/avoidance'
out.mkdir(parents=True, exist_ok=False)
names = ('velocity_controller.py', 'buffered_scan_pose.py', 'paired_scan_pose.py',
         'capture_inbox.py', 'independent_ros_clock_candidate.py',
         'fast_connected_planner_candidate.py', 'motion_forecast_trace.py')
manifest = {}
for name in names:
    data = (base/name).read_bytes()
    if name == 'velocity_controller.py':
        before = data.decode()
        start = before.index('def main():\n')
        after = before[:start]+'''def main():
    import os
    rclpy.init()
    node = None
    clock_driver = capture_driver = trace = None
    try:
        node = VelocityController()
        from avoidance.buffered_scan_pose import install
        install(node)
        from avoidance.independent_ros_clock_candidate import IndependentRosClock
        clock_driver = IndependentRosClock(node)
        from avoidance.capture_inbox import CaptureInbox
        capture_driver = CaptureInbox(node)
        recording_path = os.environ.get('AEROTHON_MOTION_FORECAST_OUT')
        if recording_path:
            from avoidance.motion_forecast_trace import MotionForecastTrace
            trace = MotionForecastTrace(node, recording_path)
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if trace is not None:
            trace.close()
        if capture_driver is not None:
            capture_driver.close()
        if clock_driver is not None:
            clock_driver.close()
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
'''
        compile(after, name, 'exec')
        data = after.encode()
    (out/name).write_bytes(data)
    manifest[name] = dict(base_sha256=hashlib.sha256((base/name).read_bytes()).hexdigest(),
                          staged_sha256=hashlib.sha256(data).hexdigest())
(out.parents[3]/'integration_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps(manifest, indent=2))
