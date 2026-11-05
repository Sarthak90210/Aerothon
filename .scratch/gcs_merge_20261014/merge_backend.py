from pathlib import Path
root = Path(__file__).resolve().parents[2]
p = root / 'src/aerothon_gcs/gcs_aggregator/gcs_aggregator/aggregator.py'
old = Path('C:/Users/sarth/.codex/worktrees/pi-web-gcs/AEROTHON/src/aerothon_gcs/gcs_aggregator/gcs_aggregator/aggregator.py').read_text()
s = p.read_text()
def function(text, name):
    start = text.index('    def ' + name + '(')
    end = text.find('\n    def ', start + 1)
    return text[start:end if end != -1 else len(text)].rstrip() + '\n\n'
s = s.replace('import threading', 'import threading\nfrom numbers import Real')
s = s.replace('from mavros_msgs.msg import State, EstimatorStatus, WaypointList', 'from mavros_msgs.msg import State, EstimatorStatus, WaypointList, Vibration, ExtendedState')
s = s.replace('from sensor_msgs.msg import BatteryState, NavSatFix, LaserScan', 'from sensor_msgs.msg import BatteryState, NavSatFix, LaserScan, MagneticField')
s = s.replace('from mission_bt import arena_dimensions', 'from mission_bt import arena_dimensions\nfrom mission_bt.delivery_zone import parse_polygon')
helper = old[old.index('def _finite_number('):old.index('SCHEMA_VERSION =')]
s = s.replace('SCHEMA_VERSION =', helper + 'SCHEMA_VERSION =', 1)
s = s.replace('        self._arm_t = None', '        self._arm_t = None\n        self._detector_stamps = {}\n        self._steady_seen = {}', 1)
s = s.replace('        self.create_subscription(BatteryState,', '''        self.create_subscription(Vibration, "/mavros/vibration/raw/vibration", self._on_vibration, qos_sensor)
        self.create_subscription(MagneticField, "/mavros/imu/mag", self._on_magnetic, qos_sensor)
        self.create_subscription(ExtendedState, "/mavros/extended_state", self._on_extended_state, qos_sensor)
        self.create_subscription(BatteryState,''')
s = s.replace('        self.pub_delivery_zone =', '        self.pub_geofence = self.create_publisher(String, "/mission/geofence", zone_qos)\n        self.pub_delivery_zone =', 1)
s = s.replace('            "power": {"volt": 0, "pct": 0},', '            "power": {"volt": None, "pct": None, "current_a": None},\n            "sensor_diagnostics": {"vibration_mps2": None, "clipping": None,\n                "magnetic_ut": None, "magnetic_strength_ut": None,\n                "magnetic_frame": None, "magnetic_capture_stamp": None},')
s = s.replace('    def _on_qr_detail(self, m):', function(old, '_detector_rate') + '    def _on_qr_detail(self, m):', 1)
for name, key in [('_on_qr_detail','qr'),('_on_banner_detail','banner'),('_on_red_detail','red')]:
    start = s.index('    def '+name+'(')
    end = s.index('\n    def ',start+1)
    block = s[start:end]
    block = block.replace('        except (ValueError, TypeError):', '        except (ValueError, TypeError):', 1)
    block = block.replace('            return\n', '            return\n        if not isinstance(d, dict):\n            return\n        self._detector_rate("'+key+'", d)\n', 1)
    s = s[:start] + block + s[end:]
s = s.replace('        self._seen[key] = time.time()', '        self._seen[key] = time.time()\n        self._steady_seen[key] = time.monotonic()')
for name, key in [('_on_state','state'),('_on_batt','power'),('_on_pose','pose'),('_on_vel','velocity'),('_on_gps','gps'),('_on_avoid','avoidance'),('_on_square_on','square'),('_on_ready','readiness'),('_on_ready_detail','readiness'),('_on_mission_state','mission')]:
    s = s.replace('    def '+name+'(self, m):\n', '    def '+name+'(self, m):\n        self._mark("'+key+'")\n', 1)
s = s.replace('        self._scan_body = m\n', '        self._scan_body = m\n        self._mark("lidar")\n',1)
start = s.index('        self.state["power"]["volt"] = round(m.voltage, 2)')
end = s.index('        self.state["safety"]["battery_ok"]',start)
s = s[:start] + '''        voltage = _finite_number(m.voltage, True)
        pct = _finite_number(m.percentage, True)
        self.state["power"]["volt"] = None if voltage is None else round(voltage, 2)
        self.state["power"]["pct"] = None if pct is None else round(pct * 100 if pct <= 1 else pct)
        self.state["power"]["current_a"] = _finite_number(m.current)
''' + s[end:]
s = s.replace('    def _on_pose(self, m):', function(old, '_on_vibration') + function(old, '_on_magnetic') + '''    def _on_extended_state(self, m):
        self._mark("extended_state")
        self.state["safety"]["on_ground"] = m.landed_state == ExtendedState.LANDED_STATE_ON_GROUND

    def _on_pose(self, m):''',1)
s = s.replace('        self._lidar_cal_refresh()\n        self._broadcast', '        self._lidar_cal_refresh()\n        now = time.monotonic()\n        self.state["sample_age_s"] = {k: round(max(0.0, now - stamp), 3) for k, stamp in self._steady_seen.items()}\n        self._broadcast',1)
s = s.replace('"oy": round(m.info.origin.position.y, 3), "data": out}', '"oy": round(m.info.origin.position.y, 3),\n                "yaw": math.radians(_euler_deg(m.info.origin.orientation)[2]),\n                "frame": m.header.frame_id,\n                "stamp": m.header.stamp.sec + m.header.stamp.nanosec / 1e9, "data": out}',1)
s = s.replace('            elif cmd == "set_delivery_zone":', '''            elif cmd == "set_geofence":
                if self.state["mission"]["armed"]:
                    return "rejected", "arena fence can only change while disarmed"
                payload = json.dumps({"vertices": args.get("vertices")})
                vertices, why = parse_polygon(payload, what="geofence")
                if vertices is None:
                    return "rejected", why
                self.pub_geofence.publish(String(data=payload))
            elif cmd == "set_delivery_zone":''',1)
p.write_text(s)
