"""Prepare a separate bounded-domain retry; preserve the original batch."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
path=Path(__file__).with_name('run_focused_clock_navigation_20261007.py')
source=path.read_text()
source=source.replace("out=root/'logs/reliability_focused_clock_navigation_20261007'",
    "out=root/'logs/reliability_focused_clock_navigation_domain_retry_20261007'")
source=source.replace("dict(condition=c,seed=s,ros_domain=229+i,rtf=2.)",
    "dict(condition=c,seed=s,ros_domain=190+i,rtf=2.)")
source=source.replace("[(c,s) for c in ('calm','field') for s in range(1,6)]",
    "[('calm',5)]+[('field',s) for s in range(1,6)]")
source=source.replace("save()\ndef run(cfg):", "assert all(0<=cfg['ros_domain']<=232 for cfg in report['configurations'])\nsave()\ndef run(cfg):")
assert 'ros_domain=229+i' not in source and 'ros_domain=190+i' in source
target=Path(__file__).with_name('run_focused_clock_navigation_domain_retry_20261007.py')
with target.open('x') as h:h.write(source)
print(target)
