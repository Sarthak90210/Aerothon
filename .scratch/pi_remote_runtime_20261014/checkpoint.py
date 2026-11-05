from pathlib import Path
import hashlib,json,datetime,zipfile
root=Path.cwd();out=root/'.scratch/pi_remote_runtime_20261014'
baseline=json.loads((out/'baseline.json').read_text())
changed={name:{'before':sha,'current':hashlib.sha256((root/name).read_bytes()).hexdigest()}
         for name,sha in baseline.items() if (root/name).is_file() and hashlib.sha256((root/name).read_bytes()).hexdigest()!=sha}
bundle=out/'runtime5.zip'
with zipfile.ZipFile(bundle) as z:manifest=json.loads(z.read('runtime_manifest.json'))
receipt=dict(status='in_progress',scope='Pi production runtime and browser, laptop-only SITL/Gazebo/gateway; dynamic banner hex codes',
  bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),source_changes=changed,source_files=manifest['files'],
  passed={'native_transport_and_execution':36,'colour_focused':216,'colour_configuration_core':100,'frontend':25,'offline_unit_before_final_guard':1955},
  pending=['Final complete offline run after integration fixes','Pi-managed rendered component runs','Pi-managed complete mission','source-matched rendered acceptance and campaign'],
  exclusions=['strong gusts','artificially delayed control'],
  unresolved=['field clearance 0.663645 m below 0.70 m','physical qualification','Pi GPIO encoder winch backend'],
  preserved_failure_logs=['focused1.log','focused2.log','focused3.log','native-final.log','offline.log','offline-3.log','offline-4.log','network-image-build.log','managed-service-install.log','logs/pi_gateway_shipped_s20261003_20261014/first_connection_failure.json'],
  laptop_addresses={'lan':'192.168.0.102','wsl':'172.26.219.3','fcu_tcp_port':5762,'sensor_http_port':19090},
  image='sha256:3b17f1eacc92891c3badb318c1a29bd7df6af4b53fb969771ead7bae5c47e51d')
(out/'progress.json').write_text(json.dumps(receipt,indent=2))
print('Checkpoint recorded; qualification remains incomplete')
