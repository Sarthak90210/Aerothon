"""Verify the immutable bundle, stop via the runtime gate, back up, then stage files."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

d=json.load(sys.stdin)
bundle=Path(d['bundle'])
assert hashlib.sha256(bundle.read_bytes()).hexdigest()==d['sha256'], 'bundle hash mismatch'
workspace=Path('/home/pi5/aerothon_ws')
backup=Path('/home/pi5/aerothon-backups/20261019-slam-ui/runtime')
backup.mkdir(mode=0o700,parents=True,exist_ok=False)
with zipfile.ZipFile(bundle) as z:
    manifest=json.loads(z.read('runtime_manifest.json'))
    for name,digest in manifest['files'].items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert hashlib.sha256(z.read(name)).hexdigest()==digest, name
    assert sorted(n for n in z.namelist() if n.endswith('.md'))==['AGENTS.md','MASTER_DOCUMENTATION.md']
    state=json.load(urllib.request.urlopen('http://127.0.0.1:8899/api/state',timeout=8))
    if not state.get('can_disconnect'):
        raise RuntimeError('Runtime disarm gate does not permit disconnect')
    request=urllib.request.Request('http://127.0.0.1:8899/api/disconnect',data=b'{}',headers={'Content-Type':'application/json'},method='POST')
    result=json.load(urllib.request.urlopen(request,timeout=35))
    assert result.get('runtime')=='Stopped', result
    subprocess.run(['systemctl','stop','aerothon-gcs.service'],check=True,timeout=70)
    (backup/'state_before.json').write_text(json.dumps(state,indent=2)+'\n')
    (backup/'disconnect_result.json').write_text(json.dumps(result,indent=2)+'\n')
    old_manifest=json.loads((workspace/'runtime_manifest.json').read_text())
    with tarfile.open(backup/'runtime_before.tar.gz','w:gz') as archive:
        old_paths=set(old_manifest['files'])|set(manifest['files'])|{'runtime_manifest.json'}
        for name in sorted(old_paths):
            p=workspace/name
            if p.is_file(): archive.add(p,arcname='workspace/'+name)
        archive.add('/home/pi5/aerothon-deploy',arcname='deployment')
        for name in ('/home/pi5/.aerothon','/home/pi5/.local/state/aerothon'):
            p=Path(name)
            if p.exists():
                archive.add(p,arcname='state/'+p.name,
                    filter=lambda info: None if any(part in ('map-tiles','roslogs') for part in Path(info.name).parts) else info)
        for name in ('/etc/systemd/system/aerothon-gcs.service','/etc/systemd/system/aerothon-router.service'):
            if Path(name).exists(): archive.add(name,arcname='systemd/'+Path(name).name)
    os.chmod(backup/'runtime_before.tar.gz',0o600)
    changed=[]
    for name,digest in manifest['files'].items():
        destination=workspace/name
        if destination.is_file() and hashlib.sha256(destination.read_bytes()).hexdigest()==digest: continue
        destination.parent.mkdir(parents=True,exist_ok=True)
        temp=destination.with_name(destination.name+'.deploy-tmp')
        temp.write_bytes(z.read(name)); os.chown(temp,1000,1000)
        os.chmod(temp,0o755 if destination.suffix=='.sh' else 0o644)
        os.replace(temp,destination)
        changed.append(name)
    target=workspace/'runtime_manifest.json'
    target.write_bytes(z.read('runtime_manifest.json')); os.chown(target,1000,1000)
    for name,digest in manifest['files'].items():
        assert hashlib.sha256((workspace/name).read_bytes()).hexdigest()==digest, name
    receipt={'bundle_sha256':d['sha256'],'verified_files':len(manifest['files']),
             'changed_files':changed,'backup':str(backup/'runtime_before.tar.gz'),
             'previous_install_preserved':str(workspace/'install'),'runtime_stopped':True,
             'destination_runtime_env_preserved':True,'hardware_calibration_preserved':True}
    (backup/'staging_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))
