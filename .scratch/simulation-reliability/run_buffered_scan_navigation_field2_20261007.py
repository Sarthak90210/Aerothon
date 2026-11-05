"""Repeat the preserved field clearance failure on the unchanged buffered source."""
from pathlib import Path
template=Path(__file__).with_name('run_buffered_scan_navigation_seed3_20261007.py').read_text()
replacements={
    'logs/reliability_buffered_scan_navigation_seed3_20261007':'logs/reliability_buffered_scan_navigation_field2_20261007',
    "seed=3,condition='calm'":"seed=2,condition='field'",
    "'calm',3,out,2.,1200.,226":"'field',2,out,2.,1200.,222",
    'my_world_calm_s3/source_manifest.json':'my_world_field_s2/source_manifest.json',
    "(out/'runner_source.py').write_bytes(Path(__file__).read_bytes())":
        "(out/'runner_source.py').write_bytes(Path(__file__).read_bytes())\n(out/'executed_runner.py').write_text(template)",
}
for old,new in replacements.items():
    assert old in template,old;template=template.replace(old,new)
exec(compile(template,str(Path(__file__).resolve()),'exec'),globals())
