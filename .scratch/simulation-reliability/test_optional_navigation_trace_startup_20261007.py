"""Execute actual navigator main with controlled startup collaborators."""
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
import pytest

root = Path(__file__).resolve().parents[2]
source = root/os.environ['AEROTHON_STARTUP_SOURCE']
sys.path.insert(0, str(source/'src/aerothon_avoidance/avoidance'))
# The review bundle contains changed files only. Model their installation
# into the existing package without changing the package or frozen source.
package_spec = importlib.util.spec_from_file_location('avoidance',
    root/'src/aerothon_avoidance/avoidance/avoidance/__init__.py',
    submodule_search_locations=[str(source/'src/aerothon_avoidance/avoidance/avoidance'),
                               str(root/'src/aerothon_avoidance/avoidance/avoidance')])
package = importlib.util.module_from_spec(package_spec)
sys.modules['avoidance'] = package
package_spec.loader.exec_module(package)
spec = importlib.util.spec_from_file_location('startup_under_review',
    source/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py')
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
from avoidance import buffered_scan_pose, independent_ros_clock_candidate, motion_forecast_trace


@pytest.mark.parametrize('recording', [False, True])
def test_normal_startup_can_run_with_or_without_explicit_diagnostic_path(recording):
    events = []
    node = SimpleNamespace(destroy_node=lambda: events.append('destroy'))
    class Clock:
        def __init__(self, value):
            assert value is node
            events.append('clock')
        def close(self):
            events.append('clock.close')
    class Trace:
        def __init__(self, value, path):
            assert value is node and path == 'explicit-diagnostic.json'
            events.append('trace')
        def close(self):
            events.append('trace.close')
    def spin(value):
        assert value is node
        events.append('spin')
        raise KeyboardInterrupt
    environment = dict(os.environ)
    environment.pop('AEROTHON_MOTION_FORECAST_OUT', None)
    if recording:
        environment['AEROTHON_MOTION_FORECAST_OUT'] = 'explicit-diagnostic.json'
    with patch.dict(os.environ, environment, clear=True), \
         patch.object(controller, 'VelocityController', return_value=node), \
         patch.object(controller.rclpy, 'init', side_effect=lambda: events.append('init')), \
         patch.object(controller.rclpy, 'spin', side_effect=spin), \
         patch.object(controller.rclpy, 'shutdown', side_effect=lambda: events.append('shutdown')), \
         patch.object(buffered_scan_pose, 'install', side_effect=lambda value: events.append('pairing')), \
         patch.object(independent_ros_clock_candidate, 'IndependentRosClock', Clock), \
         patch.object(motion_forecast_trace, 'MotionForecastTrace', Trace):
        controller.main()
    expected = ['init', 'pairing', 'clock']
    if recording:
        expected.append('trace')
    expected.append('spin')
    if recording:
        expected.append('trace.close')
    expected += ['clock.close', 'destroy', 'shutdown']
    assert events == expected
