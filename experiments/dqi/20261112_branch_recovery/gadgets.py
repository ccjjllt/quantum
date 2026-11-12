"""打印给定 paid 模式的代表性段（op 序列 + qubit），命名 gadget。"""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path

KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_branch/eae.kmx")
PAID={"CCX","CSWAP","CCZ","CCX_CARRY"}

def collect(stage, gap=50):
    inside=False; seg=[]; segs=[]; run=0
    with KMX.open("r", encoding="utf-8", errors="replace") as f:
        for l in f:
            if l.startswith("INFO_TAG "):
                tag=l.strip().split('"',2)[1]
                if tag==f"@enter:{stage}": inside=True
                elif tag==f"@exit:{stage}": inside=False
                continue
            if not inside or not l or l.startswith(("APPEND","REGISTER","SEMANTIC","ANNOTATION")): continue
            op=l.split()[0]
            if op in PAID: seg.append(l.rstrip()); run=0
            else: run+=1
            if run>=gap:
                if seg: segs.append(seg); seg=[]
    if seg: segs.append(seg)
    return segs

def shape(seg):
    c=Counter(l.split()[0] for l in seg)
    return (len(seg), c.get("CCX",0), c.get("CSWAP",0), c.get("CCZ",0), c.get("CCX_CARRY",0))

def main(stage, want, maxshow=2):
    segs=collect(stage)
    print("total segments", len(segs))
    want=tuple(int(x) for x in want.split(","))
    shown=0
    for seg in segs:
        if shape(seg)==want:
            print(f"--- shape={want} first={seg[0]} last={seg[-1]}")
            for l in seg[:60]: print("   ", l)
            shown+=1
            if shown>=maxshow: break
    # histogram of shapes with total
    h=Counter(shape(s) for s in segs)
    print("\nshape histogram (paid,ccx,cswap,ccz,carry): count -> T")
    for k,v in sorted(h.items(), key=lambda kv:-kv[0][0]*kv[1])[:25]:
        print("  ", k, "x", v, "->", k[0]*v)

if __name__=="__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv)>3 else 2)
