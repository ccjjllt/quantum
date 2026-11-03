"""Short-term ab/abc diagnostic cache spliced directly from Stage1 actual ops.

Baseline: stage1_nofallback.kmb SHA 80ba3fe75262c6cdb0b6829bfde6e368946d897b6eef2ed7e7626b6355f346a3.
- After op26111 (CCX q18 q27 q28) insert unconditional CX q28 q41 (save ab).
- After op26340 (CCX q28 q23 q40) insert unconditional CX q40 q50 (save abc).
- Delete the 12 CX q41/q50<->q28 inside the three u computations (sources were entry-zero).
- Before op30599 (stack empty) insert HMR q50 + CZ q41 q23, HMR q41 + CZ q18 q27 with fresh bits.
Keeps outer prefix/suffix identical; Z_POW identical; 62Q. Expected precise gain 0 C (diagnostic only).
"""
from __future__ import annotations
import argparse, hashlib, io, json
from pathlib import Path
import kickmix as km

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASE = ROOT/"artifacts/20261104_stage1_nofallback/invsqrt/stage1_nofallback.kmb"
DEFAULT_SHA = "80ba3fe75262c6cdb0b6829bfde6e368946d897b6eef2ed7e7626b6355f346a3"
ART = ROOT/"artifacts/20261105_shortcache/invsqrt"
FRESH0, FRESH1 = 42100, 42101

def load(path):
    raw=path.read_bytes()
    c=km.Circuit.from_file(path)
    buf=io.StringIO(); c.to_file(buf,format="kmx")
    hdr,ops=[],[]
    for line in buf.getvalue().splitlines():
        (hdr if line.startswith(("APPEND","REGISTER")) else ops).append(line)
    return c,hdr,ops,hashlib.sha256(raw).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--baseline",type=Path,default=DEFAULT_BASE)
    ap.add_argument("--baseline-sha",type=str,default=DEFAULT_SHA)
    ap.add_argument("--output",type=Path,default=ART/"shortcache_zero.kmb")
    args=ap.parse_args()
    c,hdr,ops,bsha=load(args.baseline)
    assert bsha==args.baseline_sha, f"{bsha} != {args.baseline_sha}"
    assert c.num_qubits==62
    # Locate by instruction + window content hash (Stage1 coords).
    assert ops[26111]=="CCX q18 q27 q28", ops[26111]
    assert ops[26340]=="CCX q28 q23 q40", ops[26340]
    assert ops[30599]=="CX q21 q3", ops[30599]
    win1="CCX q18 q27 q28"
    h1=hashlib.sha256(("\n".join(ops[26111:26112])).encode()).hexdigest()
    h2=hashlib.sha256(("\n".join(ops[26340:26342])).encode()).hexdigest()  # CCX + CX q40 q0
    h3=hashlib.sha256(("\n".join(ops[30594:30599])).encode()).hexdigest()  # 5-line close sequence
    # Fresh bits must not collide.
    used={int(t[1:]) for l in ops for t in l.split() if t.startswith("b") and t[1:].isdigit()}
    assert FRESH0 not in used and FRESH1 not in used, (FRESH0,FRESH1)
    # Stack must be empty at 30599.
    depth=0
    for i in range(0,30599):
        k=ops[i].split()[0]
        if k=="PUSH_CONDITION": depth+=1
        elif k=="POP_CONDITION": depth-=1
    assert depth==0, depth
    # The 12 u CX to delete: scan joint region [27775,30599) for CX coupling q41/q50 with q28.
    joint_lo, joint_hi = 27775, 30599
    dels=[]
    for i in range(joint_lo, joint_hi):
        l=ops[i]
        if l in ("CX q41 q28","CX q50 q28"):
            dels.append(i)
    assert len(dels)==12, dels
    # q41/q50 must have no writes in [25906,30599) except the two HMRs (entry-zero proof premise).
    def writes(line):
        p=line.split(); k=p[0]
        qs=[int(t[1:]) for t in p[1:] if t.startswith("q")]
        if k in ("X","CX","CCX","HMR","R"): return qs[-1:]
        if k in ("SWAP","CSWAP"): return qs[-2:]
        return []
    bad2=[(i,ops[i]) for i in range(25906,joint_hi) if 41 in writes(ops[i]) or 50 in writes(ops[i])]
    assert bad2==[], bad2
    assert ops[25897]=="HMR q50 b370", ops[25897]
    assert ops[25905]=="HMR q41 b371", ops[25905]
    # Splice.
    out=[]
    for i,l in enumerate(ops):
        if i in dels:
            continue  # delete the 12 old-zero CX
        out.append(l)
        if i==26111:
            assert l=="CCX q18 q27 q28"
            out.append("CX q28 q41")
        elif i==26340:
            assert l=="CCX q28 q23 q40"
            out.append("CX q40 q50")
    # Insert cleanup before original 30599. Account for shifts: +1 (cache1) +1 (cache2) - (#dels before 30599).
    # All 12 dels are < 30599, so net shift = 2-12 = -10. Recompute anchor by content instead of arithmetic.
    anchor=["POP_CONDITION","POP_CONDITION","POP_CONDITION","CX q21 q3"]
    # Find the POP,POP,POP,CX q21 q3 tail of joint in `out`.
    pos=None
    for i in range(len(out)-4):
        if out[i:i+4]==["POP_CONDITION","POP_CONDITION","POP_CONDITION","CX q21 q3"]:
            # ensure this is the joint end (the POP run closes b42002/b42001/b42000; preceded by PUSH b42002)
            if out[i-1]=="PUSH_CONDITION if b42002":
                pos=i
                break
    assert pos is not None
    cleanup=[f"HMR q50 b{FRESH0}",f"CZ q41 q23 if b{FRESH0}",f"HMR q41 b{FRESH1}",f"CZ q18 q27 if b{FRESH1}"]
    out[pos+3:pos+3]=cleanup  # after the 3 closing POPs, stack empty, right before CX q21 q3
    # Verify outer prefix/suffix identical (up to the three splice points).
    nc=km.Circuit.from_file(io.StringIO("\n".join(hdr+out)+"\n"),format="kmx")
    assert nc.num_qubits==62
    assert [l for l in out if l.startswith("Z_POW")] == [l for l in ops if l.startswith("Z_POW")]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    nc.to_file(args.output,format="kmb")
    csha=hashlib.sha256(args.output.read_bytes()).hexdigest()
    res={"parent_baseline_sha256":bsha,"parent_baseline_path":str(args.baseline),
         "candidate_sha256":csha,"candidate_path":str(args.output),
         "qubits":62,"operations":len(out),
         "anchor_instructions":{"op26111":ops[26111],"op26340":ops[26340],"op30599":ops[30599]},
         "window_content_hashes":{"ops26111":h1,"ops26340_26341":h2,"ops30594_30598":h3},
         "deleted_u_cx":dels,"inserted_cache":["CX q28 q41 @26111+","CX q40 q50 @26340+"],
         "inserted_cleanup":cleanup,"fresh_bits":[FRESH0,FRESH1],
         "expected_precise_gain_C":0,"diagnostic_only":True,
         "status":"built; equivalence + resource proof pending; no official verification per plan"}
    (args.output.with_suffix(".json")).write_text(json.dumps(res,indent=2)+"\n")
    print("SHORTCACHE_BUILT",csha,"Q",nc.num_qubits,"ops",len(out),flush=True)
    print(json.dumps(res,indent=2))

if __name__=="__main__":main()
