"""Separate output after the preserved invalid-domain setup rejection."""
import hashlib
from pathlib import Path
path=Path(__file__).with_name('check_clock_candidate_coupled_20261007.py')
source=path.read_text()
old="out=root/'logs/reliability_clock_candidate_coupled_20261007'"
assert source.count(old)==1
source=source.replace(old,"out=root/'logs/reliability_clock_candidate_coupled_valid_domain_20261007'")
source=source.replace("source_archive=str(archive),source_archive_sha256=", 
    "probe_source_sha256=probe_sha256,source_archive=str(archive),source_archive_sha256=")
exec(compile(source,str(path),'exec'),dict(__file__=str(path),__name__='__main__',
    probe_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
