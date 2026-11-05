"""Bitwise simulator v2: realistic inputs (syndrome qubits + mbuc bits randomized).
Usage: sim2.py KMX REGS_JSON OUT_PREFIX [N_SHOTS]"""
import sys, random, pickle, json
KMX=sys.argv[1]; PRE=sys.argv[3]; N=int(sys.argv[4]) if len(sys.argv)>4 else 2000
regs=json.load(open(sys.argv[2]))
SQ=set(regs['sq']); EB=set(regs['eb'])
random.seed(777)
ALL=(1<<N)-1
Q={}; B={}
for w in SQ: Q[w]=random.getrandbits(N)
for w in EB: B[w]=random.getrandbits(N)
def qv(w): return Q.get(w,0)
def bv(w):
    v=B.get(w)
    if v is None: v=0; B[w]=0
    return v
prod={}; branch={}
Gstack=[]; G=ALL; n=0
for line in open(KMX):
    n+=1
    c=line[0] if line else ''
    if c=='C':
        if line.startswith("CCX"):
            p=line.split()
            a,b,t=p[1].rstrip(','),p[2].rstrip(','),p[3].rstrip(',')
            pa=Q.get(a,0); pb=Q.get(b,0)
            prod[n]=(pa&pb)
            Q[t]=(Q.get(t,0)^(pa&pb&G if G!=ALL else pa&pb))
        elif line.startswith("CX"):
            p=line.split()
            if len(p)<3: continue
            x,y=p[1].rstrip(','),p[2].rstrip(',')
            if len(p)>=5 and p[-2]=='if': Q[y]=(Q.get(y,0)^(Q.get(x,0)&bv(p[-1])&G))
            elif G!=ALL: Q[y]=(Q.get(y,0)^(Q.get(x,0)&G))
            else: Q[y]=(Q.get(y,0)^Q.get(x,0))
        elif line.startswith("CSWAP"):
            p=line.split()
            if len(p)<4: continue
            x,y,z=p[1].rstrip(','),p[2].rstrip(','),p[3].rstrip(',')
            cx,cy,cz=Q.get(x,0),Q.get(y,0),Q.get(z,0)
            mm=(cx&G); dd=(cy^cz)
            Q[y]=(cy^(dd&mm)); Q[z]=(cz^(dd&mm))
    elif c=='X':
        if line.startswith("X "):
            w=line.split()[1].rstrip(','); Q[w]=(Q.get(w,0)^G)
    elif c=='H':
        if line.startswith("HMR"):
            p=line.split(); q,b=p[1],p[2]; O=random.getrandbits(N)
            if G!=ALL: Q[q]=(Q.get(q,0)&(~G&ALL)); B[b]=((B.get(b,0))&(~G&ALL))|(O&G)
            else: Q[q]=0; B[b]=O
    elif c=='S':
        if line.startswith("SWAP"):
            p=line.split(); x,y=p[1].rstrip(','),p[2].rstrip(',')
            if G!=ALL:
                dd=(Q.get(x,0)^Q.get(y,0))&G; Q[x]=(Q.get(x,0)^dd); Q[y]=(Q.get(y,0)^dd)
            else: Q[x],Q[y]=Q.get(y,0),Q.get(x,0)
    elif c=='R':
        if line.startswith('R '):
            w=line.split()[1].rstrip(',')
            if G!=ALL: Q[w]=(Q.get(w,0)&(~G&ALL))
            else: Q[w]=0
    elif c=='B':
        if line.startswith("BIT_INVERT"):
            p=line.split(); w=p[1]; e=G
            if len(p)>=4 and p[-2]=='if': e=(e&bv(p[-1]))
            B[w]=(B.get(w,0)^e)
        elif line.startswith("BIT_STORE0"):
            w=line.split()[1]; B[w]=(B.get(w,0)&(~G&ALL))
    elif c=='P':
        if line.startswith("PUSH"):
            p=line.split()
            if len(p)>=3 and p[1]=='if':
                m=p[2]; branch[m]=branch.get(m,0)+1
                Gstack.append(G); G=(G&bv(m))
            else: Gstack.append(G)
        else: G=Gstack.pop() if Gstack else ALL
print("lines",n,"prod",len(prod),"branches",len(branch),flush=True)
pickle.dump(prod,open(PRE+'_prod.pkl','wb'))
json.dump({"shots":N,"nprod":len(prod)},open(PRE+'_stats.json','w'))
