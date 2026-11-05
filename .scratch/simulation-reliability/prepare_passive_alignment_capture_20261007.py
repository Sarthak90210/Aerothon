"""Capture actual detector-identified frames during live alignment."""
from pathlib import Path
here=Path(__file__).parent
source=(here/'capture_split_unconfirmed_word_frame_20261007.py').read_text()
source=source.replace('reliability_split_unconfirmed_word_frame_20261007','reliability_split_pristine_alignment_frame_20261007')
source=source.replace('passive_unconfirmed_word_frame','passive_pristine_alignment_frame')
source=source.replace("    if not value.get('identified') or value.get('text_confirmed') or not box:return", "    if not value.get('identified') or not box:return")
source=source.replace("    if box[0]<=1 or box[1]<=1 or box[0]+box[2]>=iw-1 or box[1]+box[3]>=ih-1:return\n",'')
(here/'capture_pristine_alignment_frame_20261007.py').write_bytes(source.encode())
