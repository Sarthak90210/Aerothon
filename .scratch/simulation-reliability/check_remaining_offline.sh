#!/usr/bin/env bash
set -euo pipefail
export PATH="/home/sarthak/.nvm/versions/node/v24.18.0/bin:/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1
python3 - <<'PY'
import os,xml.dom.minidom,yaml
count=0
for root,dirs,files in os.walk('src'):
    dirs[:]=[d for d in dirs if d not in ('node_modules','__pycache__','.git','dist','build')]
    for name in files:
        path=os.path.join(root,name)
        if name.endswith(('.xml','.sdf','.xacro')):xml.dom.minidom.parse(path);count+=1
        elif name.endswith(('.yaml','.yml')):
            with open(path) as f:yaml.safe_load(f)
            count+=1
print(f'All {count} project XML/YAML files passed')
PY
bash .scratch/simulation-reliability/check_frontend.sh
git diff --check
