import sys
sys.path.insert(0,'experiments/frontier/20261116_push/chem/code3')
import numpy as np
from recode import load_words
W=load_words()
def bits(col,h,b): return np.array([(int(W[16*h+t,col])>>b)&1 for t in range(16)])
def anf(v):
    v=v.copy()
    for b in range(4):
        for lo in range(16):
            if lo&(1<<b): v[lo]^=v[lo^(1<<b)]
    return v
k=4
cols=list(range(5*k-5,5*k+5))
print('cols',cols)
for b in (1,2):
    D=np.zeros((76,16),dtype=int)
    for c in cols: 
        for h in range(76): D[h]^=bits(c,h,b)
    nonlin=0
    for h in range(76):
        a=anf(D[h])
        nonlin+=sum(1 for m in range(1,16) if bin(m).count('1')>=2 and a[m])
    print('bit',b,'XOR-of-10: blocks with nonzero nonlinear ANF coeffs:',nonlin,'of 76')
    print('   D[0]:',D[0],' anf',anf(D[0]))
    print('   D[1]:',D[1],' anf',anf(D[1]))
    print('   D[2]:',D[2],' anf',anf(D[2]))
# per-column bit1 anf degree
for c in cols:
    deg=set()
    for h in range(76):
        a=anf(bits(c,h,1))
        deg.add(max([0]+[bin(m).count('1') for m in range(16) if a[m]]))
    print('col',c,'bit1 max ANF degree over blocks:',sorted(deg))
