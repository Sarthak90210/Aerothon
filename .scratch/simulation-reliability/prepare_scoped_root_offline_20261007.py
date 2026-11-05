"""Freeze the new root escape rule before its required full offline rerun."""
from pathlib import Path
base=Path(__file__).parent
source=(base/'freeze_monotonic_escape_20261007.py').read_text().replace('monotonic_search_escape','scoped_escape_root')
source=source.replace('every observed paint rectangle','each containing observed paint margin; other margins retain full segment checks')
with (base/'freeze_scoped_escape_root_20261007.py').open('x',newline='\n') as f:f.write(source)
source=(base/'close_monotonic_escape_offline_20261007.py').read_text().replace('monotonic_search_escape','scoped_escape_root')
with (base/'close_scoped_escape_root_offline_20261007.py').open('x',newline='\n') as f:f.write(source)
print('Prepared root freeze and offline verification')
