"""Stop only owned object-navigation trials after qualification time is lost."""
import json,os,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'sim'),str(root/'scripts')]
from native_contact_evidence import qualify_vehicle_contacts
out=root/'logs'
paths=list(out.glob('reliability_reduced_v24_render_*_20261008'))
first_arm={};requested=set()
last_contact_check={}

def read_complete_rows(path):
 rows=[]
 for line in path.read_text().splitlines():
  try:rows.append(json.loads(line))
  except ValueError:pass
 return rows

def retained_contact_failure(run):
 """Only continuous valid independent evidence can trigger an early stop."""
 if time.monotonic()-last_contact_check.get(run.name,0)<30:return None
 last_contact_check[run.name]=time.monotonic()
 try:
  contacts=read_complete_rows(run/'evaluation_vehicle_contacts.jsonl')
  heartbeat=max((r['stamp'] for r in contacts if r.get('kind')=='heartbeat'),default=-1)
  onboard=[r for r in read_complete_rows(run/'onboard.jsonl') if 'flight' in r and r['stamp']<=heartbeat]
  truth=read_complete_rows(run/'evaluation_vehicle_truth.jsonl')
  layout=json.loads((run/'layout.json').read_text())
  evidence=qualify_vehicle_contacts(run,onboard,truth,layout)
  # A contact arriving after the last heartbeat cannot be judged against the
  # truncated telemetry. Allow appenders one simulated second to catch up.
  failed=[pair for pair in evidence['unexpected_contacts'] if pair['stamp']<=heartbeat-1.]
  if evidence['valid'] and evidence['ground_canary'] and failed:
   review=dict(scope='Provisional independent evidence through last heartbeat; final grader remains authoritative',
               heartbeat=heartbeat,confirmed_earlier_unexpected_pairs=failed,evidence=evidence,qualified=False)
   (run/'pre_stop_contact_diagnosis.json').write_text(json.dumps(review,indent=2))
   return f"independent contact evidence already fails acceptance: {len(failed)} unexpected pairs"
 except (OSError,ValueError,KeyError,TypeError):pass
 return None
request_code='''import rclpy,sys
from mavros_msgs.srv import SetMode
rclpy.init();n=rclpy.create_node('qualification_operator_rtl')
c=n.create_client(SetMode,'/mavros/set_mode')
if not c.wait_for_service(timeout_sec=5.):raise SystemExit('RTL service unavailable')
r=SetMode.Request();r.custom_mode='RTL';f=c.call_async(r)
rclpy.spin_until_future_complete(n,f,timeout_sec=5.)
if not f.done() or f.result() is None:raise SystemExit('RTL response missing')
print('mode_sent='+str(f.result().mode_sent),flush=True)
n.destroy_node();rclpy.shutdown()
'''
while True:
 paths=list(out.glob('reliability_reduced_v24_render_*_20261008'))
 summaries=[json.loads((p/'summary.json').read_text()) for p in paths if (p/'summary.json').exists()]
 if len(summaries)==5 or any(s.get('acceptance_pass') is False for s in summaries):break
 for run in paths:
  onboard=run/'onboard.jsonl'
  if not onboard.exists():continue
  try:
   with onboard.open('rb') as f:
    f.seek(max(0,onboard.stat().st_size-200000 if run.name in first_arm else 0));lines=f.read().splitlines()
  except OSError:
   continue
  rows=[]
  for line in lines:
   try:rows.append(json.loads(line))
   except (ValueError,UnicodeError):pass
  if not rows:continue
  row=rows[-1];flight=row.get('flight',{}).get('data',{})
  if run.name not in first_arm:
   for observed in rows:
    if observed.get('flight',{}).get('data',{}).get('armed'):
     first_arm[run.name]=observed['stamp'];break
  if run.name not in first_arm or run.name in requested or not flight.get('armed'):continue
  reason=('flight has exceeded unchanged 900 s qualification limit'
          if row['stamp']-first_arm[run.name]>901 else None)
  if reason is None and row.get('mission') in ('WINCH_DROP','RETURN_TRANSIT','RETURN_GATE_SEARCH','BANNER_ALIGN','GATE_CROSSING','RETURN_CORRIDOR','RETURN','LAND'):
   reason=retained_contact_failure(run)
  if reason is None:continue
  cfg=json.loads((run/'configuration.json').read_text())
  assert cfg['airframe']=='cad' and cfg['payload_fixture']=='loaded' and cfg['ros_domain']==30
  assert 'trial' not in cfg
  requested.add(run.name)
  receipt=dict(reason=reason,
               stamp=row['stamp'],first_observed_arm=first_arm[run.name],domain=cfg['ros_domain'])
  env=dict(os.environ,ROS_DOMAIN_ID=str(cfg['ros_domain']),ROS_LOCALHOST_ONLY='1')
  result=subprocess.run([sys.executable,'-c',request_code],env=env,capture_output=True,text=True,timeout=15)
  receipt.update(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
  (run/'operator_stop.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
 time.sleep(2)
