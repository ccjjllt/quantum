"""extract vs unextract 的 paid 门按 (op, 控制, 目标) 多重集对比。"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_branch/eae.kmx")
PAID = ("CCX", "CCZ", "CSWAP")

def main():
    stage = None
    subs = {s: Counter() for s in ("extract","unextract","unsynthesis","unconvert","convert")}
    qtarget = {s: Counter() for s in subs}
    with KMX.open("r", encoding="utf-8", errors="replace") as f:
        for l in f:
            if l.startswith("INFO_TAG "):
                try: tag = l.strip().split('"', 2)[1]
                except IndexError: continue
                if tag.startswith("@enter:") and tag[7:] in subs:
                    stage = tag[7:]
                elif tag.startswith("@exit:") and tag[6:] == stage:
                    stage = None
                continue
            if stage is None or not l or l[0] in "ARISN":
                # quick reject of APPEND/REGISTER/INFO/SEMANTIC/ANNOTATION
                if stage is None: continue
                if not (l.startswith("CCX ") or l.startswith("CCZ ") or l.startswith("CSWAP ")):
                    continue
            p = l.split()
            if stage is None: continue
            subs[stage][tuple(p)] += 1
            for q in p[1:]:
                if q.startswith("q"):
                    qtarget[stage][int(q[1:])] += 1
    for a, b in (("extract","unextract"),("convert","unconvert")):
        A, B = subs[a], subs[b]
        ta, tb = sum(A.values()), sum(B.values())
        common = sum((A & B).values())
        print(f"{a}={ta} {b}={tb} common_exact={common} only_{a}={ta-common} only_{b}={tb-common}")
        # how many unextract gates are inverses of extract gates ignoring order
        for op in PAID:
            aa = sum(v for k,v in A.items() if k[0]==op)
            bb = sum(v for k,v in B.items() if k[0]==op)
            cc = sum(v for k,v in (A & B).items() if k[0]==op)
            print(f"   {op}: {a}={aa} {b}={bb} common={cc}")
        print(f"  {b} paid per target qubit (top):", qtarget[b].most_common(12))
    # 目标分布：extract/unextract CCX 的目标是 S(<840) 还是 ancilla(>=840)
    for s in ("extract","unextract"):
        tgt = Counter()
        for k, v in subs[s].items():
            if k[0] != "CCX": continue
            t = int(k[3][1:])
            tgt["S" if t < 840 else "anc"] += v
        print(s, "CCX targets:", tgt)

if __name__ == "__main__":
    main()
