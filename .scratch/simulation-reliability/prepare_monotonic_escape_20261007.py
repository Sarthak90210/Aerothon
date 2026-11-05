"""Create a new immutable field diagnostic from current code and assets."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
base = Path(__file__).parent
for original, new in (
    ('freeze_certified_search_escape_20261007.py', 'freeze_monotonic_escape_20261007.py'),
    ('run_certified_search_escape_field_20261007.py', 'run_monotonic_escape_field_20261007.py'),
):
    source = (base / original).read_text()
    source = source.replace('certified_search_escape', 'monotonic_search_escape')
    source = source.replace('Certified nearest-edge search escapes share the router/braking predicate',
                            'Outward nearest-edge escape continuation requires nondecreasing distance to every observed paint rectangle')
    with (base / new).open('x', newline='\n') as stream:
        stream.write(source)
print('New freeze and owned trial launchers prepared; existing evidence preserved')
