"""Reuse the passive camera observer without overwriting earlier evidence."""
from pathlib import Path
source=Path(__file__).with_name('capture_split_banner_observation_20261007.py').read_text()
old='logs/reliability_split_banner_camera_review_20261007'
assert source.count(old)==1
source=source.replace(old,'logs/reliability_split_banner_current_source_camera_review_20261007')
exec(compile(source,str(Path(__file__).resolve()),'exec'),globals())
