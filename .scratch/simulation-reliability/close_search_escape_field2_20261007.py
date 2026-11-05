"""Verify every archived byte and disarm without upgrading the failed verdict."""
from pathlib import Path
here = Path(__file__).resolve().parent
source = (here/'close_capture_inbox_field23_batch_20261007.py').read_text()
source = source.replace('reliability_capture_inbox_field23_navigation_20261007', 'reliability_search_escape_field2_navigation_20261007')
source = source.replace('reliability_capture_inbox_source_20261007', 'reliability_search_escape_source_20261007')
source = source.replace('capture_inbox_candidate_20261007', 'search_escape_candidate_20261007')
source = source.replace("len(batch['results']) == 2", "len(batch['results']) == 1")
exec(compile(source, str(here/'close_capture_inbox_field23_batch_20261007.py'), 'exec'),
     dict(__file__=str(here/'close_capture_inbox_field23_batch_20261007.py'), __name__='__main__'))
