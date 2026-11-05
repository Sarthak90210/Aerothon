"""Controlled image fixtures, not recorded or fabricated flight observations."""
import hashlib,json,math
from pathlib import Path
import cv2
import numpy as np
import yaml
from partial_red_boundary_candidate_20261007 import CONFIG,partial_boundaries
root=Path(__file__).resolve().parents[2]
intrinsics=root/'logs/reliability_render_rb_rotated_s20261003_observation_repairs_20261007/runtime_parameters/11683_launch_params_dl16_imn'
hfov=float(yaml.safe_load(intrinsics.read_text())['/**']['ros__parameters']['camera_hfov'])
results=[]
assets=[]
for path in sorted((root/'src/aerothon_sim/sim_gazebo/materials').glob('qr_*.png')):
    src=cv2.imread(str(path)); assert src is not None
    # Keep the supplied binary QR pattern; red ink is a labelled fixture.
    dark=cv2.cvtColor(src,cv2.COLOR_BGR2GRAY)<128
    red_ink=np.full(src.shape,245,np.uint8);red_ink[dark]=(0,0,235)
    assets.append(dict(path=str(path.relative_to(root)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    for alt in (2.,5.,10.):
        pixels=round(1.1*1280/(2*math.tan(hfov/2)*alt))
        qr=cv2.resize(red_ink,(pixels,pixels),interpolation=cv2.INTER_NEAREST)
        for fraction in (.1,.25,.5,.75,.9,1.):
            for edge in ('top','left','bottom','right'):
                frame=np.full((720,1280,3),(160,195,130),np.uint8)
                x,y=(1280-pixels)//2,(720-pixels)//2
                visible=round(pixels*fraction)
                if edge=='top':y=visible-pixels
                elif edge=='left':x=visible-pixels
                elif edge=='bottom':y=720-visible
                else:x=1280-visible
                x0,y0=max(0,x),max(0,y);x1,y1=min(1280,x+pixels),min(720,y+pixels)
                frame[y0:y1,x0:x1]=qr[y0-y:y1-y,x0-x:x1-x]
                def project(c,wh):return cv2.approxPolyDP(c,2,True).reshape(-1,2).astype(float).tolist()
                found=partial_boundaries(frame,alt,hfov,project)
                results.append(dict(asset=path.name,altitude_m=alt,edge=edge,visible_fraction=fraction,
                                    candidates=len(found),details=found))
report=dict(scope='Controlled red-ink QR image fixtures only; no flight telemetry or success evidence',
    physical_qr_size_m=1.1,hfov_rad=hfov,config=CONFIG,assets=assets,cases=len(results),
    false_positive_cases=[r for r in results if r['candidates']],
    rejected_all=not any(r['candidates'] for r in results),rendered_qualified=False)
target=root/'logs/reliability_partial_red_qr_fixtures_intrinsics_20261007.json'
with target.open('x') as h:json.dump(report,h,indent=2)
print(json.dumps(dict(cases=len(results),rejected_all=report['rejected_all'],false_positives=len(report['false_positive_cases']))))
raise SystemExit(0 if report['rejected_all'] else 1)
