"""Matched still-air control; production and physical loop are unchanged.

The original deterministic late-scan fixture already supports drift=None.
Keep this condition distinct from every preserved default-gust failure.
"""
import argparse
import hashlib
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--kind', choices=('dirty', 'late'), required=True)
parser.add_argument('--seed', type=int, required=True)
parser.add_argument('--out', required=True)
args = parser.parse_args()
template = Path(__file__).with_name('probe_gust_margin.py')
source = template.read_text()
needle = 'case._through(drift=stress.WindDrift(seed=args.seed), **options)'
assert source.count(needle) == 1
source = source.replace(needle, 'case._through(drift=None, **options)')
source = source.replace('report = dict(seed=args.seed,',
    "report = dict(diagnostic_policy='unmodified production still-air control',"+
    "diagnostic_wind_profile='calm',probe_template_sha256=template_hash,"+
    "minimum_actual_clearance_m=None if not hasattr(case,'closest_detail') else min(slalom.gap_to(case.closest_detail['x'],case.closest_detail['y'],r) for r in slalom.WALLS+slalom.BLOCKS),seed=args.seed,")
source = source.replace('detail=case.node.last_detail))',
    "detail=case.node.last_detail))\n    if len(rows)%200==0:\n        print(json.dumps(dict(progress_stamp=case.node._now(),pose=case.node._pos)),flush=True)")
sys.argv = [str(template), '--seed', str(args.seed), '--kind', args.kind,
            '--delay', '.4', '--out', args.out]
exec(compile(source, str(template), 'exec'), dict(
    __file__=str(Path(__file__).resolve()), __name__='__main__',
    template_hash=hashlib.sha256(template.read_bytes()).hexdigest()))
