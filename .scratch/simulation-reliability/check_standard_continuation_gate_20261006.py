import importlib.util,json,tempfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('chain',Path('.scratch/simulation-reliability/continue_standard_pair_20261006.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as directory:
    out=Path(directory)
    records={'summary.json':{'acceptance_pass':False},'grade.json':{'pass':False,'checks':{}},'configuration.json':{'seed':20261003,'conditions':'calm','payload_fixture':'loaded'},'source_archive_verification.json':{'archive_verified':True}}
    for name,value in records.items():(out/name).write_text(json.dumps(value))
    try:module.qualify(out,20261003)
    except RuntimeError:print('FAIL-CLOSED gate PASS: failed acceptance cannot start next seed')
    else:raise AssertionError('Failed acceptance accepted')