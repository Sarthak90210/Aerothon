import json
import os
import sys
import cv2
import pytest

before = cv2.getNumThreads()
if len(sys.argv) > 1:
    cv2.setNumThreads(int(sys.argv[1]))
print(json.dumps({'cpu_count':os.cpu_count(),'opencv_threads_before':before,'opencv_threads':cv2.getNumThreads()}),flush=True)
raise SystemExit(pytest.main(['sim/test_banner_identity.py::ShadowRobustLetteringTests::test_the_detector_still_runs_at_camera_rate','-q','--tb=short','--durations=1']))
