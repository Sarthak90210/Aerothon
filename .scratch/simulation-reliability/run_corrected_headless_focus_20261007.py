"""One current-source navigation trial before repeating the expensive matrix."""
import json
from pathlib import Path
import signal
import sys

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
from fly_headless import fly,stop_all

out=root/'logs/reliability_corrected_headless_focus_20261007'
out.mkdir(exist_ok=False)
(out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
signal.signal(signal.SIGINT,stop_all)
signal.signal(signal.SIGTERM,stop_all)
result=fly(root/'sim/worlds/my_world.json','calm',1,out,4.,1200.,222,navigation_only=True)
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['navigation_pass'] else 1)
