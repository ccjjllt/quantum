"""Miter library: backward cone -> CNF, solver in-process with conf_budget.
Budget exhaustion is detected via model presence (UNSAT claims require proof).
"""
def parse(line):
    p=line.split()
    if not p: return ('EMPTY',)
    op=p[0]
    if op in ('CCX','CX','SWAP','HMR','X','CSWAP','CCZ','CZ','R','Z'):
        if len(p)>2 and p[-2]=='if':
            return (op,)+tuple(x.rstrip(',') for x in p[1:-2])+('IF='+p[-1],)
        return (op,)+tuple(x.rstrip(',') for x in p[1:])
    if op in ('PUSH_CONDITION','POP_CONDITION','INFO_TAG'): return (op,line.strip())
    return ('OTHER',op)

def build_cone(win, w0, l1, l2, t1, t2, max_ccx=40000, max_tot=120000, extra=()):
    """win: list of lines for [w0,l2]. Returns (rel, conds_map, frozen, bottom)."""
    conds=[()]*len(win); stack=[]
    for wi,ln in enumerate(win):
        if ln.startswith("PUSH_CONDITION"):
            p=ln.split()
            if len(p)>=3 and p[1]=='if': stack.append(p[2])
            conds[wi]=tuple(stack)
        elif ln.startswith("POP_CONDITION"):
            if stack: stack.pop()
            conds[wi]=tuple(stack)
        else: conds[wi]=tuple(stack)
    needed=set([t2]+list(extra)); rel={}; bottom=False; frozen=False
    for ln in range(l2,w0-1,-1):
        wi=ln-w0
        if wi<0 or wi>=len(win): bottom=True; break
        g=parse(win[wi]); op=g[0]
        if ln==l1 and not frozen: needed.add(t1)
        if op in ('PUSH_CONDITION','POP_CONDITION','INFO_TAG','OTHER','EMPTY'): continue
        if op in ('CCZ','CZ','Z'): continue
        cb=list(conds[wi])
        if g[-1].startswith('IF='): cb.append(g[-1][3:]); core=g[:-1]
        else: core=g
        if frozen:
            if ln==l1 and op=='CCX' and core[3]==t1:
                rel[wi]=(core,tuple(cb))
            continue
        if op=='CCX':
            _,a,b,t=core
            if t in needed:
                needed.add(a); needed.add(b); rel[wi]=(core,tuple(cb))
                if len(rel)>max_ccx: frozen=True
        elif op=='CX':
            _,x,y=core
            if y in needed:
                needed.add(x); rel[wi]=(core,tuple(cb))
                if len(rel)>max_tot: frozen=True
        elif op=='X':
            if core[1] in needed: rel[wi]=(core,tuple(cb))
        elif op=='SWAP':
            _,x,y=core
            if x in needed or y in needed:
                needed.add(x); needed.add(y); rel[wi]=(core,tuple(cb))
        elif op=='CSWAP':
            _,x,y,z=core
            if y in needed or z in needed:
                needed.add(x); needed.add(y); needed.add(z); rel[wi]=(core,tuple(cb))
        elif op=='HMR':
            if core[1] in needed: needed.discard(core[1]); rel[wi]=(core,tuple(cb))
        elif op=='R':
            if core[1] in needed: needed.discard(core[1]); rel[wi]=(core,tuple(cb))
    return rel, bottom, frozen

def build_cnf(rel, w0, l1, l2):
    clauses=[]; nxt=[1]; cur={}; bitv={}
    def new():
        v=nxt[0]; nxt[0]+=1; return v
    def CV(w):
        if w not in cur: cur[w]=new()
        return cur[w]
    def BV(b):
        if b not in bitv: bitv[b]=new()
        return bitv[b]
    def AND(o,i1,i2): clauses.extend([[-i1,-i2,o],[i1,-o],[i2,-o]])
    def XOR(o,i1,i2): clauses.extend([[-i1,-i2,-o],[i1,i2,-o],[i1,-i2,o],[-i1,i2,o]])
    def NOT(o,i1): clauses.extend([[-i1,-o],[i1,o]])
    def OR(o,i1,i2): clauses.extend([[-i1,o],[-i2,o],[i1,i2,-o]])
    def ENABLE(cb):
        e=new(); clauses.append([e]); cur_e=e
        for b in cb:
            ne=new(); AND(ne,cur_e,BV(b)); cur_e=ne
        return cur_e
    P1=P2=None
    for wi in sorted(rel):
        ln=w0+wi; core,cb=rel[wi]; op=core[0]
        e=ENABLE(cb) if cb else None
        if op=='CCX':
            _,a,b,t=core
            w=new(); AND(w,CV(a),CV(b))
            if e is not None:
                we=new(); AND(we,w,e); w=we
            o=new(); XOR(o,CV(t),w); cur[t]=o
            if ln==l1: P1=w
            if ln==l2: P2=w
        elif op=='CX':
            _,x,y=core; o=new()
            if e is not None:
                w=new(); AND(w,CV(x),e); XOR(o,CV(y),w)
            else: XOR(o,CV(y),CV(x))
            cur[y]=o
        elif op=='X':
            _,x=core; o=new()
            if e is not None: XOR(o,CV(x),e)
            else: NOT(o,CV(x))
            cur[x]=o
        elif op=='SWAP':
            _,x,y=core
            if e is None: cx,cy=CV(x),CV(y); cur[x],cur[y]=cy,cx
            else:
                cx,cy=CV(x),CV(y); ne=new(); NOT(ne,e)
                t1=new(); AND(t1,e,cy); t2=new(); AND(t2,ne,cx)
                nx=new(); OR(nx,t1,t2)
                u1=new(); AND(u1,e,cx); u2=new(); AND(u2,ne,cy)
                ny=new(); OR(ny,u1,u2)
                cur[x],cur[y]=nx,ny
        elif op=='CSWAP':
            _,x,y,z=core
            cx,cy,cz=CV(x),CV(y),CV(z)
            nx=new(); NOT(nx,cx)
            t1=new(); AND(t1,cx,cz); t2=new(); AND(t2,nx,cy)
            my=new(); OR(my,t1,t2)
            u1=new(); AND(u1,cx,cy); u2=new(); AND(u2,nx,cz)
            mz=new(); OR(mz,u1,u2)
            if e is None: cur[y],cur[z]=my,mz
            else:
                ne=new(); NOT(ne,e)
                for old,nw,key in ((cy,my,y),(cz,mz,z)):
                    q1=new(); AND(q1,e,nw); q2=new(); AND(q2,ne,old)
                    o=new(); OR(o,q1,q2); cur[key]=o
        elif op=='HMR':
            z=new()
            if e is None: clauses.append([-z])
            else:
                ne=new(); NOT(ne,e); AND(z,CV(core[1]),ne)
            cur[core[1]]=z
        elif op=='R':
            z=new(); clauses.append([-z]); cur[core[1]]=z
    if P1 is None or P2 is None: return None
    dd=new(); XOR(dd,P1,P2); clauses.append([dd])
    return clauses

def solve_cnf(clauses, conf_budget=200000):
    from pysat.solvers import Glucose4
    with Glucose4(bootstrap_with=clauses) as s:
        s.conf_budget(conf_budget)
        res=s.solve()
        if res: return 'SAT'
        # False: UNSAT or budget-out. Budget-out leaves no proof; use stats.
        st=s.accum_stats()
        if st.get('conflicts',0)>=conf_budget: return 'UNKNOWN'
        return 'UNSAT'
