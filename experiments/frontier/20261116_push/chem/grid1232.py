import numpy as np, json
NPZ="/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/chem_sub1/submission.npz"
words=np.load(NPZ,allow_pickle=False)["angle_words"].astype(np.int64)
NL,NH=16,77
T=np.zeros((NH*NL,75),dtype=np.uint8)
T[:1220]=0
for j in range(75):
    for b in range(8):
        T[:1220,j]=(words[:,j]>>b)&1 if b==0 else T[:1220,j]  # placeholder
# build truth tables properly: 8 bits per word -> but loader k only loads 5 words.
# feature analysis is per loader over its 40 bits
def mob(a,nb):
    a=a.copy()
    for b in range(nb):
        m=1<<b; idx=np.arange(len(a)); sel=(idx&m)!=0
        a[sel]^=a[idx[sel]^m]
    return a
WT=np.array([bin(m).count("1") for m in range(128)])
res=[]
for k in range(15):
    bits=np.zeros((NH*NL,40),dtype=np.uint8)
    for jj,j in enumerate(range(5*k,5*k+5)):
        for b in range(8):
            bits[:1220,jj*8+b]=(words[:,j]>>b)&1
    M=bits.reshape(NH,NL,40)
    A=np.stack([mob(M[:,:,c],4).T for c in range(40)],axis=2)  # (NH, NL, 40)? careful
    A=np.zeros_like(M)
    for c in range(40):
        for h in range(NH):
            A[h,:,c]=mob(M[h,:,c],4)
    B=np.zeros((NL,NH,40),dtype=np.uint8)
    for c in range(40):
        for f in range(NL):
            B[f,:,c]=mob(A[:,f,c],7)
    nz=np.any(B!=0,axis=2)
    prod=0; per_g={}
    for g in range(NH):
        masks={tuple(B[f,g,:].astype(int)) for f in range(1,NL) if nz[f,g]}
        if masks: per_g[g]=len(masks); prod+=len(masks)
    high=sum(1 for g in per_g if WT[g]>=2)
    highc=sum(1 for g in per_g if WT[g]>=2 and nz[0,g])
    low=sum(1 for f in range(1,NL) if bin(f).count("1")>=2 and nz[f,0])
    res.append((k,prod,high,highc,low,int(nz.sum()),sorted(per_g.values())))
    print(f"loader {k}: features {nz.sum()} products {prod} high_used {high} high_cache {highc} low {low} total_model {prod+high+low} masks/g {sorted(per_g.values())}")
print("TOTAL model",sum(r[1]+r[2]+r[4] for r in res))
