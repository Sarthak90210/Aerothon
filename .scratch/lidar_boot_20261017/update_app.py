from pathlib import Path

p = Path('src/aerothon_gcs/tauri_app/src/App.tsx')
s = p.read_text(encoding='utf-8')
marker = '// Before slam_toolbox has a map'
assert marker in s and s.rstrip().endswith('}')
s = s.split(marker)[0]
start = s.index('type Grid = {')
end = s.index('\n};', start) + len('\n};')
s = s[:start] + s[end:]
s = s.replace('import LidarCalibration from "./LidarCalibration";',
              'import LidarCalibration from "./LidarCalibration";\nimport Slam, { type Grid } from "./LidarView";')
s = s.replace('                grid={grid}', '                status={telemetry?.slam_status}\n                grid={grid}')
p.write_text(s, encoding='utf-8', newline='\n')
