import numpy as np
BUILD='/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/opencode/qcc_push/marculera_ds'
W=np.asarray(np.load(BUILD+'/submission.npz')['angle_words'],np.int64)
def affine_rep(bits):
    for a in range(16):
        c=int(bits[0])
        if all(int(bits[t])==(c ^ (bin(a&t).count('1')&1)) for t in range(16)): return a,c
    return None
for b in range(8):
    per_col=[0]*75
    for zz in range(75):
        for h in range(76):
            bits=[(int(W[16*h+t,zz])>>b)&1 for t in range(16)]
            if affine_rep(bits) is None: per_col[zz]+=1
    bad=[(z,c) for z,c in enumerate(per_col) if c]
    print('bit',b,'non-affine blocks per column: total',sum(per_col),'cols affected',len(bad), bad[:8])
