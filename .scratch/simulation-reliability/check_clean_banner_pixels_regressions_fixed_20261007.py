"""Correct the fixture filename; preserve the original pre-test setup error."""
from pathlib import Path
template=Path(__file__).with_name('check_clean_banner_pixels_regressions_20261007.py').read_text()
template=template.replace('reliability_clean_banner_pixels_regressions_20261007','reliability_clean_banner_pixels_regressions_fixed_20261007')
assert template.count('test_corruption_envelope.py')==1
template=template.replace('test_corruption_envelope.py','test_perception_corruption.py')
exec(compile(template,str(Path(__file__).resolve()),'exec'),globals())
