"""Preserve exact causal diagnosis source and expected red/green outcomes."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_causal_delay_mismatch_closed_review_20261007';out.mkdir(exist_ok=False)
proof=Path(__file__).with_name('prove_causal_delay_mismatch_20261007.py')
controller=root/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
for name,source in [('proof_source.py',proof),('controller_source.py',controller),('runner_source.py',Path(__file__))]:shutil.copy2(source,out/name)
cases=[('incorrect_exact_delay_red',[],1),('matched_fast_green',['--model-delay','.05','--expect-rejection'],0),('matched_delayed_green',['--actual-delay','.4','--model-delay','.4','--expect-rejection'],0),('zero_disturbance_guard_green',['--no-favorable-disturbance','--expect-rejection'],0)]
results=[]
for name,args,expected in cases:
 with (out/(name+'.log')).open('xb') as log:completed=subprocess.run([sys.executable,str(proof),*args],stdout=log,stderr=subprocess.STDOUT)
 text=(out/(name+'.log')).read_text();report=json.JSONDecoder().raw_decode(text)[0]
 results.append(dict(name=name,argv=args,exit_code=completed.returncode,expected_exit_code=expected,expected_result_observed=completed.returncode==expected,measurements=report))
review=dict(scope='Causal diagnosis and isolated admission guard only; no mission or gust qualification',results=results,all_expected_outcomes=all(r['expected_result_observed'] for r in results),production_adopted=False,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*source.py')})
(out/'review.json').write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps(review,indent=2));raise SystemExit(0 if review['all_expected_outcomes'] else 1)
