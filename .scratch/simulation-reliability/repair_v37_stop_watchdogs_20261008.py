"""Future native/campaign supervisors retain timeouts and retry safe requests."""
from pathlib import Path
base=Path(__file__).resolve().parent
for stem in ['watch_v37_native_failed_trials_20261008.py','watch_v37_campaign_failed_trials_20261008.py']:
    p=base/stem;s=p.read_text()
    s=s.replace('first_arm={};requested=set()','first_arm={};requested=set();attempts={}')
    s=s.replace('  requested.add(run.name)', '  attempts[run.name]=attempts.get(run.name,0)+1')
    old="""  result=subprocess.run([sys.executable,'-c',request_code],env=env,capture_output=True,text=True,timeout=15)
  receipt.update(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)"""
    new="""  receipt['attempt']=attempts[run.name]
  try:
   result=subprocess.run([sys.executable,'-c',request_code],env=env,capture_output=True,text=True,timeout=15)
   receipt.update(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
  except subprocess.TimeoutExpired as exc:
   def readable(value):return value.decode(errors='replace') if isinstance(value,bytes) else value or ''
   receipt.update(returncode=None,timeout_s=15,stdout=readable(exc.stdout),stderr=readable(exc.stderr))
  if 'mode_sent=True' in receipt['stdout']:requested.add(run.name)
  (run/f"operator_stop_attempt_{attempts[run.name]}.json").write_text(json.dumps(receipt,indent=2))"""
    assert old in s,stem
    s=s.replace(old,new);compile(s,str(p),'exec');p.write_text(s,encoding='utf-8',newline='\n')
    print(stem)
