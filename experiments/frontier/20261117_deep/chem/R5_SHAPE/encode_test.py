import numpy as np
z=np.load('experiments/frontier/20261117_deep/chem/data/dfthcsos/submission.npz')
U=z['U']; aw=z['angle_words']; edges=z['tree_edges']; R,B,N=U.shape
brot=8
def encode(v,edges,brot=8):
    u=np.array(v,dtype=float).copy()
    words=np.zeros(len(edges),dtype=np.int64)
    for t in range(len(edges)-1,-1,-1):
        p,c=edges[t]
        th=np.arctan2(u[c],u[p])
        if th<0: th+=2*np.pi
        words[t]=int(np.round(th/np.pi*(1<<(brot-1)))) & ((1<<brot)-1)
        u[p]=np.hypot(u[p],u[c]); u[c]=0.0
    return words,u
def decode(words,edges,brot=8):
    v=np.zeros(len(edges)+1); v[0]=1.0
    for t,(p,c) in enumerate(edges):
        th=np.pi*words[t]/(1<<(brot-1))
        a,b=v[p],v[c]
        v[p]=np.cos(th)*a-np.sin(th)*b
        v[c]=np.sin(th)*a+np.cos(th)*b
    return v
rows=U.reshape(-1,N)
# compare decoded shipped words to shipped U
maxdiff=0; overlaps=[]
for k in range(rows.shape[0]):
    d=decode(aw[76+k],edges)
    ov=abs(d@rows[k])/np.linalg.norm(d)
    overlaps.append(ov)
    maxdiff=max(maxdiff,np.linalg.norm(d-rows[k]))
print('decoded shipped words vs shipped U: maxdiff',maxdiff,'overlap min/max',min(overlaps),max(overlaps))
# encode shipped U rows, compare words
for k in [0,1,2,10,100]:
    w,uend=encode(rows[k],edges,brot)
    diff=np.abs(w-aw[76+k]); diff=np.minimum(diff,256-diff)
    print('row',k,'word diff max',diff.max(),'mean',diff.mean(),'end',np.linalg.norm(uend-np.eye(N)[0]))
# random vector roundtrip
rng=np.random.default_rng(0)
for trial in range(3):
    v=rng.standard_normal(N); v/=np.linalg.norm(v)
    w,uend=encode(v,edges,brot); d=decode(w,edges,brot)
    print('random',trial,'roundtrip err',np.linalg.norm(d-v),'norm',np.linalg.norm(d),'end',np.linalg.norm(uend-np.eye(N)[0]))
