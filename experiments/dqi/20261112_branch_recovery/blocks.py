"""用 '廉价门长间隙' 切分 unextract，统计每段 paid 门数分布，识别 gadget 规模。"""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path

KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_branch/eae.kmx")
PAID = {"CCX","CSWAP","CCZ","CCX_CARRY"}
CHEAP = {"CX","SWAP","X","Z","CZ","HMR","R","BIT_INVERT","BIT_STORE0","BIT_STORE1","NEG","PUSH_CONDITION","POP_CONDITION"}

def main(stage, gap):
    inside=False; seg=[]; segs=[]; ln=0; run=0
    with KMX.open("r", encoding="utf-8", errors="replace") as f:
        for l in f:
            ln+=1
            if l.startswith("INFO_TAG "):
                tag=l.strip().split('"',2)[1]
                if tag==f"@enter:{stage}": inside=True
                elif tag==f"@exit:{stage}": inside=False
                continue
            if not inside or not l or l.startswith(("APPEND","REGISTER","SEMANTIC","ANNOTATION")):
                continue
            op=l.split()[0]
            if op in PAID:
                seg.append(op); run=0
            else:
                run+=1
            if run>=gap:
                if seg: segs.append(Counter(seg)); seg=[]
    if seg: segs.append(Counter(seg))
    tot=sum(sum(c.values()) for c in segs)
    print(f"stage={stage} gap={gap} segments={len(segs)} total_paid={tot}")
    h=Counter()
    for c in segs:
        h[(sum(c.values()), c.get("CCX",0), c.get("CSWAP",0), c.get("CCZ",0))]+=1
    for k,v in sorted(h.items(), key=lambda kv:-kv[0][0]*kv[1])[:40]:
        print(f"   paid={k[0]:6d} CCX={k[1]:6d} CSWAP={k[2]:5d} CCZ={k[3]:4d}  x{v}   -> {k[0]*v}")
    print("  total by size>=100:", sum(k[0]*v for k,v in h.items() if k[0]>=100))
    print("  total by size<100 :", sum(k[0]*v for k,v in h.items() if k[0]<100))

if __name__=="__main__":
    main(sys.argv[1], int(sys.argv[2]))
