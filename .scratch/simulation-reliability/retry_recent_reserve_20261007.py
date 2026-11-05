"""Keep the failed setup logs and launch the corrected guard adapter separately."""
from pathlib import Path
base=Path(__file__).parent
source=(base/'run_recent_reserve_coupled_20261007.sh').read_text()
source=source.replace('reliability_recent_reserve_coupled_20261007','reliability_recent_reserve_coupled_retry_20261007')
with (base/'run_recent_reserve_coupled_retry_20261007.sh').open('x',newline='\n') as f:f.write(source)
print('Prepared retry; original guard mismatch remains preserved as setup failure')
