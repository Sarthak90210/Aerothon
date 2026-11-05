"""Preserve the red-capable timer/probe regressions in the offline suite."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
for source,target in [('test_retry_observation_windows.py','test_delivery_retry_observation_windows.py'),
                      ('test_provisional_release_probe.py','test_delivery_provisional_release_probe.py')]:
    path=root/'sim'/target
    assert not path.exists(),f'Refuse to overwrite {path}'
    text=(Path(__file__).parent/source).read_text().replace('parents[2]','parents[1]')
    path.write_text(text)
    print(target)
