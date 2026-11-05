"""Improve sample construction while preserving exact endpoint and count rules."""
from pathlib import Path
here=Path(__file__).parent
source=(here/'batched_certificate_candidate_20261007.py').read_text()
old='    points=np.concatenate(segments) if segments else np.zeros((1,2))'
new='''    if segments and isinstance(segments[0],tuple):
        starts=np.asarray([a for a,b in segments])
        ends=np.asarray([b for a,b in segments])
        counts=np.array([max(2,int(math.dist(a,b)/.05)+2) for a,b in segments])
        indices=np.arange(int(max(counts)))[:,None]
        fractions=indices/(counts[None,:]-1)
        values=starts[None,:,:]+fractions[:,:,None]*(ends-starts)[None,:,:]
        # numpy.linspace forces both endpoints, including its final value.
        values[0,:,:]=starts
        values[counts-1,np.arange(len(counts)),:]=ends
        points=values.transpose(1,0,2)[(indices<counts[None,:]).T]
    else:
        points=np.concatenate(segments) if segments else np.zeros((1,2))'''
assert source.count(old)==1;source=source.replace(old,new)
source=source.replace('segments.append(sample_segment(point,nxt))','segments.append((point.copy(),nxt.copy()))')
(here/'vectorized_certificate_candidate_20261007.py').write_bytes(source.encode())
for old_name,new_name in [('check_batched_certificate_zero_time_20261007.py','check_vectorized_certificate_zero_time_20261007.py'),
                           ('benchmark_batched_publication_20261007.py','benchmark_vectorized_publication_20261007.py')]:
    text=(here/old_name).read_text().replace('batched_certificate_candidate_20261007','vectorized_certificate_candidate_20261007')
    text=text.replace('reliability_batched_certificate_zero_time_20261007','reliability_vectorized_certificate_zero_time_20261007')
    text=text.replace('reliability_batched_publication_benchmark_20261007','reliability_vectorized_publication_benchmark_20261007')
    (here/new_name).write_bytes(text.encode())
print('Prepared vectorized sample construction with full unchanged segment sample counts/endpoints')
