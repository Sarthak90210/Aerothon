"""Resolve imports under each owned Python node's actual recorded environment."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
out=Path(sys.argv[1]).resolve();snapshot=Path(sys.argv[2]).resolve()
owned=json.loads((out/'runtime_configuration_manifest.json').read_text())['owned_group']
frozen=json.loads((snapshot/'diagnostic_source_manifest.json').read_text())
results=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  pid=int(p.name)
  if os.getpgid(pid)!=owned:continue
  argv=[a.decode() for a in (p/'cmdline').read_bytes().split(b'\0') if a]
  if not any('/lib/avoidance/velocity_controller' in a or '/lib/mission_bt/mission_tree' in a for a in argv):continue
  env=dict(a.decode().split('=',1) for a in (p/'environ').read_bytes().split(b'\0') if b'=' in a)
  code="import inspect,json;from avoidance import velocity_controller,capture_inbox,independent_ros_clock_candidate;from mission_bt import mission_tree;print(json.dumps([inspect.getfile(m) for m in (velocity_controller,capture_inbox,independent_ros_clock_candidate,mission_tree)]))"
  modules=json.loads(subprocess.check_output(['/usr/bin/python3','-c',code],cwd=(p/'cwd').resolve(),env=env,text=True))
  entries=[]
  for module in modules:
   resolved=Path(module).resolve();relative=str(resolved.relative_to(snapshot));sha=hashlib.sha256(resolved.read_bytes()).hexdigest()
   assert frozen[relative]==sha,(relative,sha)
   entries.append(dict(module_path=module,resolved_source_path=str(resolved),source_sha256=sha,matches_frozen=True))
  results.append(dict(pid=pid,argv=argv,modules=entries,environment_keys_used=['PYTHONPATH','AMENT_PREFIX_PATH'],other_environment_values_disclosed=False))
 except (OSError,ProcessLookupError):continue
assert any(any("/lib/avoidance/velocity_controller" in a for a in r["argv"]) for r in results), results
report=dict(scope='Read-only import resolution under owned node environments; no controller callback or parameter writes',owned_group=owned,all_match_frozen=True,mission_entrypoint_verification=any(any("/lib/mission_bt/mission_tree" in a for a in r["argv"]) for r in results),nodes=results)
with (out/'owned_node_import_resolution_20261007.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report,indent=2))
