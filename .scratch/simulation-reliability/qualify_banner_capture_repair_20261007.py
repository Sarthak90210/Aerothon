"""Freeze the new camera boundary, then run the suite and native split course."""
from pathlib import Path
path=Path(__file__).with_name('qualify_observation_repairs_20261007.py')
source=path.read_text()
source=source.replace('reliability_observation_and_capture_qualification_20261007',
                      'reliability_banner_capture_qualification_20261007')
source=source.replace('reliability_full_observation_and_capture_20261007.log',
                      'reliability_full_banner_capture_20261007.log')
source=source.replace("for world in ('shipped','rb_rotated','split_corridors'):",
                      "for world in ('split_corridors',):")
source=source.replace('observation_repairs_20261007', 'banner_capture_20261007')
source=source.replace("    assert all(frozen.get(key)==value for key,value in core.items()), 'Decision producer changed'",
    "    decision_changed=any(frozen.get(key)!=value for key,value in core.items())\n    assert decision_changed, 'Expected capture boundary repair absent'")
source=source.replace('decision_source_matches_passing_standard_pair=True',
                      'decision_source_matches_passing_standard_pair=False')
source=source.replace("changed_layers=['headless observations/receipt/evidence','runtime capture output scope']",
    "changed_layers=['timestamped banner captures and onboard pose pairing','distinct dwell frames','OCR cache continuity','headless capture metadata']")
source=source.replace("report['note']='Changing-gust repair and corrected broader campaign remain required'",
    "report['note']='Targeted split course only; standard pair, shipped and rotated must be repeated on this source. Changing-gust and broader campaign remain unqualified'")
exec(compile(source,str(path),'exec'),dict(__file__=str(path),__name__='__main__'))
