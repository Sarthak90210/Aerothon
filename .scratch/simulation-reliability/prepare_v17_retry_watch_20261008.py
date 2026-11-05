from pathlib import Path
base=Path(__file__).resolve().parent
text=(base/'watch_v17_failed_trials_20261008.py').read_text().replace('reliability_reduced_v17_targeted_20261008','reliability_reduced_v17_normal_timing_retry_20261008')
text=text.replace("  with onboard.open('rb') as f:\n   f.seek(max(0,onboard.stat().st_size-200000 if run.name in first_arm else 0));lines=f.read().splitlines()", "  try:\n   with onboard.open('rb') as f:\n    f.seek(max(0,onboard.stat().st_size-200000 if run.name in first_arm else 0));lines=f.read().splitlines()\n  except OSError:\n   continue")
(base/'watch_v17_retry_failed_trials_20261008.py').write_text(text,newline='\n')
text=(base/'watch_v17_failed_trials_20261008.sh').read_text().replace('watch_v17_failed_trials','watch_v17_retry_failed_trials')
(base/'watch_v17_retry_failed_trials_20261008.sh').write_text(text,newline='\n')
