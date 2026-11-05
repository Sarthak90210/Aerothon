import sys,collections
from load import *
m=load_module(sys.argv[1]) if len(sys.argv)>1 else load_module()
e=m.ScanOdometry(); out=[]
for i,(c,t) in enumerate(zip(clouds,stamps)):
    try: p,q=e.update(c,t); out.append(('T',i,p,q))
    except ValueError as x: out.append(('H',i,str(x)))
print(collections.Counter(o[0]+(o[2] if o[0]=='H' else '') for o in out))
s=''.join(o[0] for o in out); print(s)
tr=[o for o in out if o[0]=='T']
print('last tracking pose', tr[-1][2] if tr else None, 'tracking count',len(tr))
