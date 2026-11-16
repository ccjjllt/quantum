import numpy as np
NPZ="/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/chem_sub1/submission.npz"
words=np.load(NPZ,allow_pickle=False)["angle_words"].astype(np.int64)
def mob(a,nb):
    a=a.copy()
    for b in range(nb):
        m=1<<b; idx=np.arange(len(a)); sel=(idx&m)!=0
        a[sel]^=a[idx[sel]^m]
    return a
tot=0
for k in range(15):
    delta=words[:,5*k:5*k+5].copy()
    if k: delta^=words[:,5*k-5:5*k]
    packed=np.zeros(1232,dtype=np.uint64)
    for j in range(5):
        packed[:len(delta)] |= (delta[:,j].astype(np.uint64)&127)<<(7*j)
    f=packed.reshape(77,16).copy()
    for b in range(4):
        for lo in range(16):
            if lo&(1<<b): f[:,lo]^=f[:,lo^(1<<b)]
    for b in range(7):
        for hi in range(77):
            if hi&(1<<b): f[hi]^=f[hi^(1<<b)]
    # per high monomial h: 15 low monomials x 35 outputs
    nprod=0; ngroups=0
    for h in range(77):
        rows={}
        for l in range(1,16):
            v=int(sum(int(f[h,l])<<((l2-1)*35) for l2 in [])) if False else None
        # build 35-bit pattern per low monomial
        pats={}
        for l in range(1,16):
            pats[l]=int(f[h,l])
        groups={}
        for l,p in pats.items(): groups.setdefault(p,[]).append(l)
        for p,g in groups.items():
            if p: nprod+=(len(g)+1)//2; ngroups+=1
    print(f"loader {k}: high monomials used {sum(1 for h in range(77) if any(int(f[h,l]) for l in range(1,16)))}"
          f"  paired products {nprod}  unpaired groups {ngroups}")
    tot+=nprod
print("total paired products",tot,"per pass; + cache 75*15 =",tot+75*15,"  (shipped 4025)")
