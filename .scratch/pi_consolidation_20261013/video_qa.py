import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
video = root / 'logs/pi_cleanup_hard_field_both_s20261004_retry1_20261013/overview/world_overview.mp4'
out = Path(__file__).parent / 'video_qa'
out.mkdir(exist_ok=True)
probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_format',
    '-show_streams', '-of', 'json', str(video)]))
(out / 'ffprobe.json').write_text(json.dumps(probe, indent=2))
duration = float(probe['format']['duration'])
for name, stamp in [('start', 5), ('search', 450), ('clearance_failure', 783), ('disarmed', duration - 1)]:
    subprocess.run(['ffmpeg', '-v', 'error', '-n', '-ss', str(stamp), '-i', str(video),
                    '-frames:v', '1', str(out / f'{name}.png')], check=True)
stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
print(json.dumps(dict(duration_s=duration, codec=stream['codec_name'], width=stream['width'],
    height=stream['height'], frames=stream.get('nb_frames'), sample_frames=str(out)), indent=2))
