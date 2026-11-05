"""Repeat the preserved failing physical cases without modifying their fixture."""
from pathlib import Path

source_path = Path(__file__).with_name('check_buffered_scan_coupled_20261007.py')
source = source_path.read_text()
old = "out=root/'logs/reliability_buffered_scan_coupled_20261007'"
assert source.count(old) == 1
source = source.replace(old, "out=root/'logs/reliability_buffered_scan_coupled_repeat_20261007'")
exec(compile(source, str(source_path), 'exec'), dict(__file__=str(source_path), __name__='__main__'))
