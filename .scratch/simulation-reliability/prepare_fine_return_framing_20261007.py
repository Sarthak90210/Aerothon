"""Reuse the verified freeze machinery for a separately archived candidate."""
from pathlib import Path
base=Path(__file__).parent
source=(base/'freeze_oblique_observer_20261007.py').read_text()
source=source.replace('certified_search_escape','monotonic_search_escape')
source=source.replace('oblique_observer','fine_return_framing')
source=source.replace('ObliqueObserverReturnBanner','FineReturnFraming')
source=source.replace("mission_tree.FindReturnBanner=FineReturnFraming", "mission_tree.AlignToBanner=FineReturnFraming")
source=source.replace("='RETURN_GATE_SEARCH'", "='BANNER_ALIGN'")
source=source.replace('fine_return_framing_return_candidate_20261007.py','fine_return_framing_candidate_20261007.py')
source=source.replace('Isolated camera observer handoff on oblique identification plus certified search escapes',
                      'Isolated fine return yaw sweep and high-altitude look restoration plus monotonic search escapes')
with (base/'freeze_fine_return_framing_20261007.py').open('x',newline='\n') as stream:stream.write(source)
print('Prepared isolated fine framing freeze')
