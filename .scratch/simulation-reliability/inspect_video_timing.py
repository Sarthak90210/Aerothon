import subprocess
import sys
from pathlib import Path
root=Path(sys.argv[1])
for name in ('onboard_sim_time_corrected.ffconcat','onboard_sim_time_corrected.mp4'):
    extra=['-safe','0','-f','concat'] if name.endswith('.ffconcat') else []
    data=subprocess.check_output(['ffprobe','-v','error',*extra,'-i',str(root/name),
        '-select_streams','v:0','-show_entries','packet=pts_time,duration_time',
        '-of','csv=p=0'],text=True).splitlines()
    print(name,len(data),data[:5],data[-5:])
