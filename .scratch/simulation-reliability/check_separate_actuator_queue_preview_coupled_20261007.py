"""Combined isolated disturbance feed-through model and queue preview."""
from pathlib import Path
import sys
here=Path(__file__).resolve().parent
source=(here/'check_command_deadline_coupled_20261007.py').read_text().replace('reliability_command_deadline_coupled_20261007','reliability_separate_actuator_queue_preview_coupled_20261007')
needle='summary=[]\n';assert source.count(needle)==1
source=source.replace(needle,"from actuator_disturbance_forecast_candidate_20261007 import install as forecast_install\nfrom queue_preview_candidate_20261007 import install as preview_install\nforecast_install(velocity_controller.VelocityController,out/'forecast_source')\npreview_install(velocity_controller.VelocityController,out/'compensation_source')\n"+needle)
sys.path.insert(0,str(here))
exec(compile(source,str(here/'check_command_deadline_coupled_20261007.py'),'exec'),dict(__file__=str(here/'check_command_deadline_coupled_20261007.py'),__name__='__main__'))
