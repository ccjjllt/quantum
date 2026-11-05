"""Prove CCX product equals a live wire at same line: P(c&d@L) == V(w@L).
UNSAT => replace `CCX c d u` with `CX w u` (exact, single line).
Usage: wireprove.py KMX OFFS CAND_JSON OUT_JSON TL"""
import sys, json
sys.path.insert(0,'experiments/dqi/20261106_stagebulk')
from miter import build_cone
KMX,OFFS,CAND,OUT,TL=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],float(sys.argv[5])
c=json.load(open(CAND)); L=c['L']; w=c['w']
offs=json.load(open(OFFS))
LB=60000
w0=max(1,L-LB); win=[]
with open(KMX,'rb') as f:
    f.seek(offs[(w0-1)//512]); cur=((w0-1)//512)*512
    while cur<w0-1: f.readline(); cur+=1
    while cur<L:
        b=f.readline()
        if not b: break
        win.append(b.decode()); cur+=1
print(f"window [{w0},{L}] lines={len(win)}",flush=True)
import time; t0=time.time()
rel,bottom,frozen=build_cone(win,w0,L,L,c['t'],c['t'],max_ccx=10**9,max_tot=10**9,extra=(c['a'],c['b'],w))
print(f"cone rel={len(rel)} bottom={bottom} frozen={frozen} t={round(time.time()-t0,1)}",flush=True)
if bottom or frozen or len(rel)>800000:
    json.dump({"status":'OPEN',"cone":len(rel)},open(OUT,'w')); print("OPEN",flush=True); sys.exit()
from ortools.sat.python import cp_model
m=cp_model.CpModel(); cur={}; bitv={}
def CV(x):
    if x not in cur: cur[x]=m.NewBoolVar(f"w{x}")
    return cur[x]
def BV(b):
    if b not in bitv: bitv[b]=m.NewBoolVar(f"b{b}")
    return bitv[b]
def AND3(o,a,b): m.AddAllowedAssignments([a,b,o],[(0,0,0),(0,1,0),(1,0,0),(1,1,1)])
def XOR3(o,a,b): m.AddAllowedAssignments([a,b,o],[(0,0,0),(0,1,1),(1,0,1),(1,1,0)])
def OR3(o,a,b): m.AddAllowedAssignments([a,b,o],[(0,0,0),(0,1,1),(1,0,1),(1,1,1)])
P1=None
for wi in sorted(rel):
    ln=w0+wi; core,cb=rel[wi]; op=core[0]
    e=None
    if cb:
        e=m.NewBoolVar(f"e{wi}"); m.Add(e==1)
        for b in cb:
            ne=m.NewBoolVar(f"eb{wi}"); AND3(ne,e,BV(b)); e=ne
    if op=='CCX':
        _,a,b,t=core
        wv=m.NewBoolVar(f"w{wi}"); AND3(wv,CV(a),CV(b))
        if e is not None:
            we=m.NewBoolVar(f"we{wi}"); AND3(we,wv,e); wv=we
        o=m.NewBoolVar(f"o{wi}"); XOR3(o,CV(t),wv); cur[t]=o
        if ln==L: P1=wv
    elif op=='CX':
        _,x,y=core; o=m.NewBoolVar(f"o{wi}")
        if e is not None:
            ww=m.NewBoolVar(f"w{wi}"); AND3(ww,CV(x),e); XOR3(o,CV(y),ww)
        else: XOR3(o,CV(y),CV(x))
        cur[y]=o
    elif op=='X':
        _,x=core; o=m.NewBoolVar(f"o{wi}")
        if e is not None: XOR3(o,CV(x),e)
        else: m.Add(o==CV(x).Not())
        cur[x]=o
    elif op=='SWAP':
        _,x,y=core
        if e is None: cx,cy=CV(x),CV(y); cur[x],cur[y]=cy,cx
        else:
            cx,cy=CV(x),CV(y); ne=m.NewBoolVar(f"ne{wi}"); m.Add(ne==e.Not())
            t1=m.NewBoolVar(f"t1{wi}"); AND3(t1,e,cy); t2=m.NewBoolVar(f"t2{wi}"); AND3(t2,ne,cx)
            nx=m.NewBoolVar(f"nx{wi}"); OR3(nx,t1,t2)
            u1=m.NewBoolVar(f"u1{wi}"); AND3(u1,e,cx); u2=m.NewBoolVar(f"u2{wi}"); AND3(u2,ne,cy)
            ny=m.NewBoolVar(f"ny{wi}"); OR3(ny,u1,u2)
            cur[x],cur[y]=nx,ny
    elif op=='CSWAP':
        _,x,y,z=core
        cx,cy,cz=CV(x),CV(y),CV(z)
        nx=m.NewBoolVar(f"nx{wi}"); m.Add(nx==cx.Not())
        t1=m.NewBoolVar(f"t1{wi}"); AND3(t1,cx,cz); t2=m.NewBoolVar(f"t2{wi}"); AND3(t2,nx,cy)
        my=m.NewBoolVar(f"my{wi}"); OR3(my,t1,t2)
        u1=m.NewBoolVar(f"u1{wi}"); AND3(u1,cx,cy); u2=m.NewBoolVar(f"u2{wi}"); AND3(u2,nx,cz)
        mz=m.NewBoolVar(f"mz{wi}"); OR3(mz,u1,u2)
        if e is None: cur[y],cur[z]=my,mz
        else:
            ne=m.NewBoolVar(f"ne{wi}"); m.Add(ne==e.Not())
            for old,nw,key in ((cy,my,y),(cz,mz,z)):
                q1=m.NewBoolVar(f"q1{wi}{key}"); AND3(q1,e,nw)
                q2=m.NewBoolVar(f"q2{wi}{key}"); AND3(q2,ne,old)
                o=m.NewBoolVar(f"o{wi}{key}"); OR3(o,q1,q2)
                cur[key]=o
    elif op=='HMR':
        z=m.NewBoolVar(f"z{wi}")
        if e is None: m.Add(z==0)
        else:
            ne=m.NewBoolVar(f"ne{wi}"); m.Add(ne==e.Not()); AND3(z,CV(core[1]),ne)
        cur[core[1]]=z
    elif op=='R':
        z=m.NewBoolVar(f"zr{wi}"); m.Add(z==0); cur[core[1]]=z
if P1 is None:
    json.dump({"status":'NOPROD',"cone":len(rel)},open(OUT,'w')); print("NOPROD",flush=True); sys.exit()
P2=CV(w)
m.Add(P1!=P2)
s=cp_model.CpSolver(); s.parameters.max_time_in_seconds=TL; s.parameters.num_search_workers=8
t0=time.time(); st=s.StatusName(s.Solve(m)); dt=round(time.time()-t0,1)
verdict='WIREQ' if st=='INFEASIBLE' else ('DIFF' if st in ('OPTIMAL','FEASIBLE') else 'UNKNOWN:'+st)
json.dump({"status":verdict,"cone":len(rel),"L":L,"solve_s":dt},open(OUT,'w'))
print(verdict,"solve_s=",dt,flush=True)
