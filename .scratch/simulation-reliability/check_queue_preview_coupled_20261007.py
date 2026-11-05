"""Unchanged coupled physical gust/delay fixtures; isolated queue preview."""
from pathlib import Path
import sys
here=Path(__file__).resolve().parent
source=(here/'check_command_deadline_coupled_20261007.py').read_text()
source=source.replace('reliability_command_deadline_coupled_20261007','reliability_queue_preview_coupled_20261007')
needle='summary=[]\n';assert source.count(needle)==1
source=source.replace(needle,"from queue_preview_candidate_20261007 import install\ninstall(velocity_controller.VelocityController,out/'compensation_source')\n"+needle)
sys.path.insert(0,str(here))
exec(compile(source,str(here/'check_command_deadline_coupled_20261007.py'),'exec'),dict(__file__=str(here/'check_command_deadline_coupled_20261007.py'),__name__='__main__'))
