"""Finish launcher registration and close the unchanged root offline freeze."""
from pathlib import Path
base=Path(__file__).parent
source=(base/'run_monotonic_escape_field_20261007.py').read_text()
source=source.replace('monotonic_search_escape','fine_return_framing')
with (base/'run_fine_return_framing_field_20261007.py').open('x',newline='\n') as f:f.write(source)
source=(base/'close_search_campaign_offline_20261007.py').read_text()
source=source.replace('reliability_search_braking_campaign_full_offline','reliability_monotonic_search_escape_full_offline')
source=source.replace('reliability_certified_search_escape_source','reliability_monotonic_search_escape_source')
with (base/'close_monotonic_escape_offline_20261007.py').open('x',newline='\n') as f:f.write(source)
print('Prepared candidate launcher and exact-source offline closure')
