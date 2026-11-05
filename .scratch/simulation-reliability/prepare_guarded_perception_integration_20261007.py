"""Queue concrete checked repairs behind the current immutable recording."""
from pathlib import Path
here=Path(__file__).parent
source=(here/'qualify_pristine_banner_20261007.py').read_text()
source=source.replace('reliability_pristine_banner_qualification_20261007','reliability_early_red_clipped_bearing_qualification_20261007')
source=source.replace('pristine_banner_pixels_20261007','early_red_clipped_bearing_20261007')
source=source.replace("('split_corridors',)","('split_corridors','rb_rotated')")
source=source.replace("'pristine analysis pixels and separate display overlays'", "'pristine analysis pixels and separate display overlays','provisional camera red boundaries','brake before exclusion replanning','clipped banner bearing before area range'")
source=source.replace('standard pair, shipped and rotated must be repeated','standard pair and shipped must be repeated')
(here/'qualify_early_red_clipped_bearing_20261007.py').write_bytes(source.encode())
print('Prepared complete offline and split/rotated rendered qualifier')
