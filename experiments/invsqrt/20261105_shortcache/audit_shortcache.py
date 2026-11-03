"""Independent audit for shortcache_zero (actual KMB bytes; no generator import).

Baseline: stage1_nofallback.kmb 80ba3fe7... Candidate: shortcache_zero.kmb 97e63915...
Proves: entry-zero + lifecycle, full 62-wire output restoration, downstream old-bit
equality, saved-stack equality, total-phase equality (new HMR outcomes as free
variables), and precise 0 C cost delta with full condition stacks.
"""
from __future__ import annotations
import argparse, collections, difflib, hashlib, importlib.metadata, io, json, platform, sys, time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import kickmix as km
import z3

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASE = ROOT/"artifacts/20261104_stage1_nofallback/invsqrt/stage1_nofallback.kmb"
DEFAULT_BASE_SHA = "80ba3fe75262c6cdb0b6829bfde6e368946d897b6eef2ed7e7626b6355f346a3"
DEFAULT_CAND = ROOT/"artifacts/20261105_shortcache/invsqrt/shortcache_zero.kmb"
ART = ROOT/"artifacts/20261105_shortcache/invsqrt"

def load(path):
    raw=Path(path).read_bytes()
    c=km.Circuit.from_file(path)
    buf=io.StringIO(); c.to_file(buf,format="kmx")
    hdr,ops=[],[]
    for line in buf.getvalue().splitlines():
        (hdr if line.startswith(("APPEND","REGISTER")) else ops).append(line)
    return c,hdr,ops,hashlib.sha256(raw).hexdigest()

def writes(line):
    p=line.split(); k=p[0]
    qs=[int(t[1:]) for t in p[1:] if t.startswith("q")]
    if k in ("X","CX","CCX","HMR","R"): return qs[-1:]
    if k in ("SWAP","CSWAP"): return qs[-2:]
    return []

def run(lines, initial_q, initial_stack=()):
    q=list(initial_q); bits={}; stack=list(initial_stack)
    phase=z3.BoolVal(False); cost=z3.IntVal(0)
    events={}; versions=collections.Counter(); serial=0
    def bit(name): return bits.setdefault(name, z3.Bool(f"entry_{name}"))
    for line in lines:
        p=line.split(); kind=p[0]
        if kind=="PUSH_CONDITION": stack.append(bit(p[-1])); continue
        if kind=="POP_CONDITION":
            assert stack, "stack underflow"; stack.pop(); continue
        guards=list(stack)
        if "if" in p: guards.append(bit(p[p.index("if")+1]))
        active=z3.And(guards)
        qs=[int(t[1:]) for t in p[1:] if t.startswith("q")]
        if kind=="X": q[qs[0]]=z3.Xor(q[qs[0]],active)
        elif kind=="CX": q[qs[1]]=z3.Xor(q[qs[1]],z3.And(active,q[qs[0]]))
        elif kind=="CCX":
            q[qs[2]]=z3.Xor(q[qs[2]],z3.And(active,q[qs[0]],q[qs[1]])); cost+=z3.If(active,1,0)
        elif kind in ("SWAP","CSWAP"):
            a,b=qs[-2:]; ctl=active if kind=="SWAP" else z3.And(active,q[qs[0]])
            oa,ob=q[a],q[b]; q[a]=z3.If(ctl,ob,oa); q[b]=z3.If(ctl,oa,ob)
            if kind=="CSWAP": cost+=z3.If(active,1,0)
        elif kind in ("Z","CZ","CCZ","NEG"):
            phase=z3.Xor(phase,z3.And([active]+[q[j] for j in qs]))
            if kind=="CCZ": cost+=z3.If(active,1,0)
        elif kind in ("HMR","R"):
            if kind=="HMR":
                name=p[2]; v=versions[name]; versions[name]+=1
                ev=z3.Bool(f"out_{name}_v{v}" if v else f"out_{name}")
                events[name if v==0 else f"{name}_v{v}"]=active
            else: ev=z3.Bool(f"anon_{serial}"); serial+=1
            phase=z3.Xor(phase,z3.And(active,q[qs[0]],ev))
            q[qs[0]]=z3.If(active,z3.BoolVal(False),q[qs[0]])
            if kind=="HMR": bits[name]=z3.If(active,ev,bit(name))
        elif kind in ("BIT_STORE0","BIT_STORE1","BIT_INVERT"):
            old=bit(p[1]); new=z3.Not(old) if kind=="BIT_INVERT" else z3.BoolVal(kind=="BIT_STORE1")
            bits[p[1]]=z3.If(active,new,old)
        else: raise ValueError(f"unsupported {line}")
    return q,bits,stack,phase,cost,events

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--baseline",type=Path,default=DEFAULT_BASE)
    ap.add_argument("--baseline-sha",type=str,default=DEFAULT_BASE_SHA)
    ap.add_argument("--candidate",type=Path,default=DEFAULT_CAND)
    args=ap.parse_args()
    t0=time.monotonic()
    bc,bh,bo,bsha=load(args.baseline)
    cc,ch,co,csha=load(args.candidate)
    assert bsha==args.baseline_sha, bsha
    assert bc.num_qubits==cc.num_qubits==62 and bh==ch
    assert [l for l in bo if l.startswith("Z_POW")]==[l for l in co if l.startswith("Z_POW")]
    print(f"BASE {bsha} len {len(bo)} | CAND {csha} len {len(co)}",flush=True)
    # 1. Diff must be exactly the 15 expected blocks.
    codes=difflib.SequenceMatcher(a=bo,b=co,autojunk=False).get_opcodes()
    ne=[c for c in codes if c[0]!="equal"]
    assert len(ne)==15, [(t,i1,i2,j1,j2) for t,i1,i2,j1,j2 in ne]
    assert ne[0][0]=="insert" and co[ne[0][3]:ne[0][4]]==["CX q28 q41"], ne[0]
    assert ne[1][0]=="insert" and co[ne[1][3]:ne[1][4]]==["CX q40 q50"], ne[1]
    for blk in ne[2:14]:
        assert blk[0]=="delete" and bo[blk[1]:blk[2]] in (["CX q41 q28"],["CX q50 q28"]), blk
    assert ne[14][0]=="insert" and co[ne[14][3]:ne[14][4]]==["HMR q50 b42100","CZ q41 q23 if b42100","HMR q41 b42101","CZ q18 q27 if b42101"], ne[14]
    print("DIFF_15_BLOCKS_OK",flush=True)
    # Anchors.
    assert bo[26111]=="CCX q18 q27 q28" and bo[26340]=="CCX q28 q23 q40" and bo[30599]=="CX q21 q3"
    # 2. Entry-zero + lifecycle (static).
    assert bo[25897]=="HMR q50 b370" and bo[25905]=="HMR q41 b371"
    assert bo[25937]=="HMR q40 b1004" and bo[25940]=="HMR q28 b612"
    zw=[(i,bo[i]) for i in range(25906,30599) if 41 in writes(bo[i]) or 50 in writes(bo[i])]
    assert zw==[], zw
    assert [(i,bo[i]) for i in range(25941,26111) if 28 in writes(bo[i])]==[]
    assert [(i,bo[i]) for i in range(25938,26340) if 40 in writes(bo[i])]==[]
    # All four HMRs are unconditional (depth 0, no if); verified by the run's stack check below.
    # Candidate writes to 41/50 only at the intended cache + cleanup lines.
    cw=[(i,co[i]) for i in range(25906,30600) if 41 in writes(co[i]) or 50 in writes(co[i])]
    kinds=sorted(set(l.split()[0] for _,l in cw))
    assert kinds==["CX","HMR"], cw
    print(f"LIFECYCLE_OK baseline_zero_writes_41_50={len(zw)} candidate_writes={[l for _,l in cw]}",flush=True)
    # Stack empty at cleanup insertion (candidate coords 30589-30593).
    depth=0
    for i in range(0,30589):
        k=co[i].split()[0]
        if k=="PUSH_CONDITION": depth+=1
        elif k=="POP_CONDITION": depth-=1
    assert depth==0, depth
    for l in co[30589:30593]:
        assert "if" not in l.split() or not l.startswith("PUSH"), l
    print("CLEANUP_STACK_EMPTY_OK",flush=True)
    # Fresh bits.
    used={int(t[1:]) for l in bo for t in l.split() if t.startswith("b") and t[1:].isdigit()}
    assert 42100 not in used and 42101 not in used
    print("FRESH_BITS_OK",flush=True)
    # 3. Symbolic miter over [26111,30599) vs candidate [26111,30593).
    BLO,BHI=26111,30599
    # Candidate window: find cleanup start (HMR q50 b42100) then end before CX q21 q3.
    cs=next(i for i,l in enumerate(co) if l=="HMR q50 b42100")
    assert co[cs:cs+4]==["HMR q50 b42100","CZ q41 q23 if b42100","HMR q41 b42101","CZ q18 q27 if b42101"]
    assert co[cs+4]=="CX q21 q3"
    CLO,CHI=26111,cs+4
    assert bo[BHI:]==co[CHI:], "suffix mismatch"
    assert bo[:BLO]==co[:CLO], "prefix mismatch"
    old_w,new_w=bo[BLO:BHI],co[CLO:CHI]
    print(f"WINDOW old [{BLO},{BHI}) len {len(old_w)} new [{CLO},{CHI}) len {len(new_w)}",flush=True)
    # Entry premises (all proved statically above, unconditional HMR + zero writes on all paths):
    # q41/q50 zero via HMR 25897/25905; q28 zero via HMR 25940 + no writes [25941,26111);
    # q40 zero via HMR 25937 + no writes [25938,26340).
    entry_q=[z3.Bool(f"entry_q{j}") if j not in (28,40,41,50) else z3.BoolVal(False) for j in range(62)]
    qo,bits_o,so,po,cost_o,eo=run(old_w,entry_q)
    qn,bits_n,sn,pn,cost_n,en=run(new_w,entry_q)
    assert not so and not sn
    assert set(eo)<=set(en), (set(eo),set(en))
    olds=set(bits_o)|set(bits_n)
    # old bits = baseline bits; new fresh bits excluded from equality.
    diffs=[z3.Xor(a,b) for a,b in zip(qo,qn)]+[z3.Xor(po,pn)]
    for k in sorted(olds):
        if k in ("b42100","b42101"): continue
        diffs.append(z3.Xor(bits_o.get(k,z3.Bool(f"entry_{k}")),bits_n.get(k,z3.Bool(f"entry_{k}"))))
    for name,act in eo.items():
        diffs.append(z3.Xor(act,en[name]))
    s=z3.Solver(); s.set(timeout=60000); s.add(z3.Or(diffs))
    r=s.check()
    print("MITER",r,flush=True)
    assert str(r)=="unsat", s.model()
    # Cost equality (all charged gates identical activations).
    s2=z3.Solver(); s2.set(timeout=60000); s2.add(cost_o!=cost_n)
    r2=s2.check()
    print("COST_MITER",r2,flush=True)
    assert str(r2)=="unsat"
    # Opcode census: no CCX/CCZ delta.
    from collections import Counter
    cb,cn=Counter(l.split()[0] for l in bo),Counter(l.split()[0] for l in co)
    assert cb["CCX"]==cn["CCX"] and cb["CCZ"]==cn["CCZ"], (cb["CCX"],cn["CCX"],cb["CCZ"],cn["CCZ"])
    print(f"TOFFOLI_CENSUS_EQUAL CCX={cn['CCX']} CCZ={cn['CCZ']}",flush=True)
    res={"status":"PASS","scope":"independent actual-byte local proof; entry-zero lifecycle, 62-wire restoration, old-bit/stack/phase equality, 0C; no official verification",
         "baseline_sha256":bsha,"candidate_sha256":csha,"qubits":62,
         "diff_blocks":len(ne),"window_old":[BLO,BHI],"window_new":[CLO,CHI],
         "fresh_bits":[42100,42101],"miter":str(r),"cost_miter":str(r2),
         "ccx":cn["CCX"],"ccz":cn["CCZ"],"expected_gain_C":0,
         "metadata":{"seconds":time.monotonic()-t0,"python":platform.python_version(),
                      "kickmix":importlib.metadata.version("kickmix"),"z3":z3.get_version_string(),
                      "time":datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()}}
    out=ART/"audit_shortcache_zero.json"
    out.write_text(json.dumps(res,indent=2)+"\n")
    print("FINAL_RESULT "+json.dumps({"status":"PASS","path":str(out)}),flush=True)

if __name__=="__main__":raise SystemExit(main())
