"""How does the loader's address cache scale with the number of loaded words?
Measures, on the shipped delta table, #high monomials (mask 1..76, wt>=2) and
#feature columns needed for a J-word batch, for J = 3,4,5."""
import numpy as np, itertools
NPZ="/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/chem_sub1/submission.npz"
words=np.load(NPZ,allow_pickle=False)["angle_words"].astype(np.int64)
def mob(a,nb):
    a=a.copy()
    for b in range(nb):
        m=1<<b; idx=np.arange(len(a)); sel=(idx&m)!=0
        a[sel]^=a[idx[sel]^m]
    return a
def analyse(cols):
    """cols: list of word indices; returns (#high masks used, #nonconstant low columns, #product cols)"""
    delta=words[:,cols].copy()
    if min(cols)>0: delta^=words[:,np.array(cols)-5]
    packed=np.zeros(1232,dtype=np.uint64)
    for j in range(len(cols)):
        packed[:len(delta)] |= (delta[:,j].astype(np.uint64)&127)<<(7*j)
    f=packed.reshape(77,16).copy()
    for b in range(4):
        for lo in range(16):
            if lo&(1<<b): f[:,lo]^=f[:,lo^(1<<b)]
    for b in range(7):
        for hi in range(77):
            if hi&(1<<b): f[hi]^=f[hi^(1<<b)]
    high=set(); cols_used=0
    for h in range(77):
        pats=[int(f[h,l]) for l in range(1,16)]
        if any(pats):
            high.add(h); cols_used+=sum(1 for p in pats if p)
    return len([h for h in high if bin(h).count('1')>=2]), cols_used
for J in (3,4,5):
    hs=[];cs=[]
    for k in range(15):
        base=5*k
        cols=list(range(base,base+J))
        h,c=analyse(cols); hs.append(h); cs.append(c)
    print(f"J={J}: high masks {np.mean(hs):.1f} (min {min(hs)} max {max(hs)})  product columns {np.mean(cs):.1f}")
    # per-loader cost estimate: products = columns/2, cache = high masks + 6 low
    prod=np.mean(cs)/2; cache=np.mean(hs)+6
    per=prod+cache; K=int(np.ceil(75/J))
    T=2*K*per+6662; Q=84+J*8+303
    print(f"      per-loader {per:.1f} -> K={K} L/pass {K*per:.0f} T {T:.0f} Q {Q} cost {46.9216*T*Q/1e6:.2f}M")
