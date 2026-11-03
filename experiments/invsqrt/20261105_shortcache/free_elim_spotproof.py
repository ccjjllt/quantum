"""Exact Z3 spot-miturs for step-4.1 cache-template refutations (shortcache_zero coords).

Legal-prefix SSA miter (entry x in [1,3133452], HMR outcomes symbolic, PUSH captures).
60s timeout -> UNKNOWN. Saves verdict + counterexample x per (op, template).
Covers: top firing CCZs x cache-wire templates (the only novel cases vs prior work);
plain templates on firing CCZs are already screen-refuted with saved samples.
"""
from __future__ import annotations
import argparse, hashlib, io, json, time
from pathlib import Path
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
CAND = ROOT/"artifacts/20261105_shortcache/invsqrt/shortcache_zero.kmb"
CSHA = "97e6391503cb463a72666a393d9c20b1b5f18359c79d89b1ff76157eff21e9da"
ART = ROOT/"artifacts/20261105_shortcache/invsqrt"

def load():
    assert hashlib.sha256(CAND.read_bytes()).hexdigest()==CSHA
    c=km.Circuit.from_file(CAND)
    buf=io.StringIO(); c.to_file(buf,format="kmx")
    lines=buf.getvalue().splitlines()
    return [l for l in lines if not l.startswith(("APPEND","REGISTER"))]

def prove_gate(ops,op,replacement,timeout_ms=60000):
    import z3
    start=time.monotonic()
    s=z3.Solver(); s.set(timeout=timeout_ms)
    q=[z3.Bool(f'x{j}') for j in range(22)]+[z3.BoolVal(False)]*40
    bits={}; stack=[]; serial=0
    xv=z3.Sum([z3.If(q[j],1<<j,0) for j in range(22)])
    s.add(xv>=1,xv<=3133452)
    def fresh(expr):
        nonlocal serial
        ex=z3.simplify(expr)
        if z3.is_true(ex) or z3.is_false(ex): return ex
        out=z3.Bool(f't{serial}'); serial+=1; s.add(out==ex); return out
    for i,line in enumerate(ops[:op+1]):
        p=line.split(); k=p[0]
        if k=='PUSH_CONDITION': stack.append(bits.get(int(p[-1][1:]),z3.BoolVal(False))); continue
        if k=='POP_CONDITION':
            if stack: stack.pop()
            continue
        active=z3.And(*stack) if stack else z3.BoolVal(True)
        if 'if' in p: active=z3.And(active,bits.get(int(p[p.index('if')+1][1:]),z3.BoolVal(False)))
        qs=[int(t[1:]) for t in p[1:] if t.startswith('q')]
        if i==op:
            old=z3.And(*(q[j] for j in (qs if k=='CCZ' else qs[:2])))
            new=z3.BoolVal(False)
            if replacement=='delete': pass
            elif replacement.startswith('Z q'):
                u=int(replacement.split()[1][1:]); new=q[u]
            elif replacement.startswith('CZ '):
                _,a,b=replacement.split(); new=z3.And(q[int(a[1:])],q[int(b[1:])])
            else: raise ValueError(replacement)
            s.add(active,z3.Xor(old,new)); break
        if k=='X': q[qs[0]]=fresh(z3.Xor(q[qs[0]],active))
        elif k=='CX': q[qs[1]]=fresh(z3.Xor(q[qs[1]],z3.And(active,q[qs[0]])))
        elif k=='CCX': q[qs[2]]=fresh(z3.Xor(q[qs[2]],z3.And(active,q[qs[0]],q[qs[1]])))
        elif k in ('SWAP','CSWAP'):
            a,b=qs[-2:]; ctl=active if k=='SWAP' else z3.And(active,q[qs[0]])
            oa,ob=q[a],q[b]; q[a]=fresh(z3.If(ctl,ob,oa)); q[b]=fresh(z3.If(ctl,oa,ob))
        elif k in ('HMR','R'):
            q[qs[0]]=fresh(z3.And(q[qs[0]],z3.Not(active)))
            if k=='HMR':
                b=int(p[2][1:]); out=z3.Bool(f'm{i}'); bits[b]=fresh(z3.If(active,out,bits.get(b,z3.BoolVal(False))))
        elif k.startswith('BIT_'):
            b=int(p[1][1:]); old=bits.get(b,z3.BoolVal(False))
            new=z3.Not(old) if k=='BIT_INVERT' else z3.BoolVal(k=='BIT_STORE1')
            bits[b]=fresh(z3.If(active,new,old))
    res=s.check()
    rec={'op':op,'original':ops[op],'replacement':replacement,'verdict':str(res),
         'ssa_nodes':serial,'seconds':time.monotonic()-start}
    if res==z3.sat:
        m=s.model()
        rec['counterexample_x']=sum((1<<j) for j in range(22) if z3.is_true(m.eval(z3.Bool(f'x{j}'),model_completion=True)))
    if res==z3.unknown: rec['reason']=s.reason_unknown()
    return rec

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,default=ART/"free_elim_spotproofs.json")
    args=ap.parse_args()
    ops=load()
    # Top firing CCZs x cache-wire templates (novel vs prior work).
    pairs=[(26655,'CZ q41 q23'),(26655,'CZ q50 q14'),(26655,'Z q41'),
           (27227,'CZ q41 q23'),(27227,'CZ q50 q14'),(27227,'Z q50')]
    rows=[prove_gate(ops,op,r) for op,r in pairs]
    for r in rows: print(json.dumps(r),flush=True)
    doc={"candidate_sha256":CSHA,"pairs":pairs,"results":rows,
         "rule":"sat=refuted (counterexample x saved); unsat=proved; unknown=timeout, not claimed",
         "status":"spot proofs only; full 38-CCZ screen refutations are in free_elim_screen.json"}
    args.output.write_text(json.dumps(doc,indent=2)+"\n")
    print("WROTE "+str(args.output),flush=True)

if __name__=="__main__":main()
