import json,os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];run=root/'logs/reliability_reduced_v9_targeted_20261008/my_world_random_s3'
config=json.loads((run/'configuration.json').read_text());assert config['ros_domain']==41 and config['navigation_only']
text=(root/'.scratch/simulation-reliability/watch_v9_failed_trials_20261008.py').read_text()
namespace={};exec(text[text.index("request_code="):text.index("while not")],namespace)
result=subprocess.run([sys.executable,'-c',namespace['request_code']],env=dict(os.environ,ROS_DOMAIN_ID='41',ROS_LOCALHOST_ONLY='1'),capture_output=True,text=True,timeout=15)
receipt=dict(reason='900 s limit exceeded during QR search; repeated unchanged-margin turn braking diagnosed',domain=41,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
(run/'operator_stop.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
