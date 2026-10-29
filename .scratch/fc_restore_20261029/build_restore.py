"""The FC's working configuration of 29 Oct 2026 as a Mission Planner .param
file, to restore it after the operator's parameter reset.

Base: the full read at 00:51 (fc_params_reference_20261029_0051.json, 1298
parameters, fc_read_params.py through the Pi's router). On top, every change
written after it and read back on the aircraft:
  ~01:00 osd_elrs_20261029  ExpressLRS MAVLink on TELEM1, DJI OSD on TELEM2
  03:20  rc6_winch_20261029 output 5 left to the Pi (no FC function, no mount)
Left out: counters and values the FC sets itself at boot.

    python build_restore.py      # writes fc_restore_20261029.param
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
base = json.loads((HERE / "fc_params_reference_20261029_0051.json").read_text())

LATER = {
    # osd_elrs_20261029 (set and read back, FC rebooted)
    "SERIAL1_PROTOCOL": 2, "MAV2_RAW_SENS": 1, "MAV2_EXT_STAT": 1, "MAV2_RC_CHAN": 1,
    "MAV2_POSITION": 1, "MAV2_EXTRA1": 1, "MAV2_EXTRA2": 1, "MAV2_EXTRA3": 1,
    "MAV2_OPTIONS": 2, "BRD_SER2_RTSCTS": 0,
    # rc6_winch_20261029: the Pi drives output 5 with DO_SET_SERVO
    "SERVO5_FUNCTION": 0, "MNT1_TYPE": 0,
}
SKIP = re.compile(r"^(STAT_|FORMAT_VERSION$|SYSID_SW_|BARO\d?_GND_|GND_ABS_PRESS|GND_TEMP"
                  r"|STAT_RESET|INS_ACC\d?_ID$|INS_GYR\d?_ID$|COMPASS_DEV_ID|BARO\d_DEVID)")

missing = [k for k in LATER if k not in base]
if missing:
    raise SystemExit(f"not in the reference: {missing}")
out = dict(base)
out.update({k: float(v) for k, v in LATER.items()})
lines = [f"{k},{v:.9g}" for k, v in sorted(out.items()) if not SKIP.match(k)]
skipped = sorted(k for k in out if SKIP.match(k))
(HERE / "fc_restore_20261029.param").write_text(
    "# AeroTHON FC configuration of 29 Oct 2026 (00:51 read + ELRS/OSD ~01:00 + output 5 to the Pi 03:20)\n"
    + "\n".join(lines) + "\n", encoding="ascii")
print(len(lines), "parameters written;", len(skipped), "left out:", " ".join(skipped))
for k in ("SERVO5_FUNCTION", "MNT1_TYPE", "SERIAL5_PROTOCOL", "SERIAL5_BAUD", "SERIAL1_PROTOCOL",
          "SERIAL1_BAUD", "SERIAL2_PROTOCOL", "SERIAL2_BAUD", "FRAME_CLASS", "FRAME_TYPE",
          "GPS1_TYPE", "OSD_TYPE", "RSSI_TYPE", "MAV3_RC_CHAN"):
    print(f"  {k} = {out.get(k)}")
