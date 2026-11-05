"""Postflight diagnostic figure from archived exact observer/certificate reproduction."""
import json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
root=Path(__file__).resolve().parents[2]
evidence=root/'logs/reliability_causal_delay_mismatch_closed_review_20261007'
proof=(evidence/'proof_source.py').read_text()
proof=proof.replace("root=Path(__file__).resolve().parents[2];path=root/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'", "root=Path(__file__).resolve().parents[2];path=Path(archived_controller)")
proof=proof.replace('position=0.;minimum=wall;dt=.01','position=0.;minimum=wall;dt=.01;physical_curve=[]')
proof=proof.replace('minimum=min(minimum,wall-position)','minimum=min(minimum,wall-position);physical_curve.append((float(t+dt),wall-position))')
proof=proof.replace("assert not accepted or minimum>=.7,'Causal false disturbance from exact latency assumption admits unsafe motion'", "")
sys.argv=[str(evidence/'proof_source.py')]
ns=dict(__file__=str(evidence/'proof_source.py'),__name__='__main__',archived_controller=str(evidence/'controller_source.py'))
exec(compile(proof,str(evidence/'proof_source.py'),'exec'),ns)
forecast=[(i*.05+.05,ns['wall']-p[1]) for i,p in enumerate(ns['seen'])]
physical=ns['physical_curve']
curve=evidence/'zero_wind_predicted_actual_clearance_curves_20261007.json'
with curve.open('x') as f:json.dump(dict(scope='Controlled zero-wind counterexample; not a rendered flight',forecast=forecast,physical=physical,required_clearance_m=.7,planning_threshold_m=.725),f,indent=2)
fig,ax=plt.subplots(figsize=(8.5,4.2),layout='constrained')
ax.plot(*np.array(forecast).T,label='Production certificate: assumed 0.40 s receipt',color='#2166ac',linewidth=2)
ax.plot(*np.array(physical).T,label='Physical fixture: actual 0.05 s receipt, zero wind',color='#b35806',linewidth=2)
ax.axhline(.7,color='#b2182b',linestyle='--',label='Required clearance 0.70 m')
ax.axhline(.725,color='#555555',linestyle=':',label='Planning threshold 0.725 m')
ax.set(xlabel='Future time from captured state (s)',ylabel='Wall clearance (m)',title='Exact receipt delay mismatch admits an unsafe pulse')
ax.grid(alpha=.2);ax.legend(fontsize=8,loc='upper right');ax.set_ylim(.3,1.2)
path=evidence/'zero_wind_predicted_actual_clearance_20261007.png'
assert not path.exists();fig.savefig(path,dpi=180)
print(path)
