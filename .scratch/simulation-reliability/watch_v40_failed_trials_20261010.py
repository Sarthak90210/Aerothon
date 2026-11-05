"""Stop only owned object-navigation trials after qualification time is lost."""
import json,os,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_reduced_v40_targeted_20261010'
first_arm={};requested=set();attempts={}
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
while not (out/'report.json').exists():
 for run in out.glob('my_world_*'):
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
  if (run.name not in first_arm or run.name in requested or not flight.get('armed')
      or row['stamp']-first_arm[run.name]<=901):continue
  cfg=json.loads((run/'configuration.json').read_text())
  assert cfg['navigation_only'] and not cfg['artificial_transport_delay_injected']
  attempts[run.name]=attempts.get(run.name,0)+1
  receipt=dict(reason='flight has exceeded unchanged 900 s qualification limit',
               stamp=row['stamp'],first_observed_arm=first_arm[run.name],domain=cfg['ros_domain'])
  env=dict(os.environ,ROS_DOMAIN_ID=str(cfg['ros_domain']),ROS_LOCALHOST_ONLY='1')
  receipt['attempt']=attempts[run.name]
  try:
   result=subprocess.run([sys.executable,'-c',request_code],env=env,capture_output=True,text=True,timeout=15)
   receipt.update(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
  except subprocess.TimeoutExpired as exc:
   def readable(value):return value.decode(errors='replace') if isinstance(value,bytes) else value or ''
   receipt.update(returncode=None,timeout_s=15,stdout=readable(exc.stdout),stderr=readable(exc.stderr))
  if 'mode_sent=True' in receipt['stdout']:requested.add(run.name)
  (run/f"operator_stop_attempt_{attempts[run.name]}.json").write_text(json.dumps(receipt,indent=2))
  (run/'operator_stop.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
 time.sleep(2)
