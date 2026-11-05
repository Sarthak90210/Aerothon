"""Preserved physical coupled cases, isolated zero-disturbance admission guard."""
from pathlib import Path
import sys
here=Path(__file__).resolve().parent
source=(here/'check_command_deadline_coupled_20261007.py').read_text()
source=source.replace('reliability_command_deadline_coupled_20261007','reliability_no_favorable_disturbance_coupled_retry_20261007')
needle='summary=[]\n'
assert source.count(needle)==1
source=source.replace(needle,"from no_favorable_disturbance_candidate_20261007 import install\ninstall(velocity_controller.VelocityController,out/'forecast_source')\n"+needle)
sys.path.insert(0,str(here))
exec(compile(source,str(here/'check_command_deadline_coupled_20261007.py'),'exec'),dict(__file__=str(here/'check_command_deadline_coupled_20261007.py'),__name__='__main__'))
