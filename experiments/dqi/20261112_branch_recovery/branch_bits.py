"""分支位普查：REGISTER 位宽、HMR 站点、PUSH_CONDITION、1-bit 量子 flag（CSWAP/CX 控制）。"""
from __future__ import annotations
import re
from collections import Counter, defaultdict
from pathlib import Path

KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_branch/eae.kmx")

def main():
    regs=[]; bits_total=0
    stage=None
    hmr=Counter(); push=Counter(); ops=Counter()
    single_ctl_cswap=Counter()   # CSWAP 控制位（1 qubit）
    stage_qubits=defaultdict(set)
    quse=Counter()
    with KMX.open("r", encoding="utf-8", errors="replace") as f:
        for l in f:
            if l.startswith("REGISTER "):
                m=re.match(r'REGISTER (r\d+) "(.*)"', l.strip())
                if m: regs.append((m.group(1), m.group(2)))
                continue
            if l.startswith("INFO_TAG "):
                tag=l.strip().split('"',2)[1]
                if tag.startswith("@enter:") and tag[7:] in ("extract","synthesis","convert","scan","unconvert","unsynthesis","unextract","mask_projection","initial"):
                    stage=tag[7:]
                elif tag.startswith("@exit:") and tag[6:]==stage:
                    stage=None
                continue
            if not l or l.startswith(("APPEND","SEMANTIC","ANNOTATION")): continue
            p=l.split(); op=p[0]
            ops[op]+=1
            if op=="HMR": hmr[stage]+=1
            if op=="PUSH_CONDITION": push[stage]+=1
            if op=="CSWAP" and stage:
                single_ctl_cswap[stage]+=1
            for q in p[1:4]:
                if q.startswith("q"): quse[int(q[1:])]+=1
    # bit registers: names
    names=Counter(n for _,n in regs)
    print("registers:", len(regs), "distinct names:", len(names))
    print("  sample:", list(names.items())[:6], "...")
    widths=Counter()
    for n,c in names.items():
        widths[len(n)]+=c
    print("  name-length histogram:", dict(sorted(widths.items())))
    print("  total num_bits (from verifier log): 151525 ; 4095 E regs x 12 = 49140")
    print("HMR per stage:", dict(hmr))
    print("PUSH_CONDITION per stage:", dict(push))
    print("CSWAP per stage:", dict(single_ctl_cswap))
    print("top ops:", dict(sorted(ops.items(), key=lambda kv:-kv[1])[:16]))
    # 量子 flag：只出现在 CSWAP 控制位且总使用次数很少的 qubit
    low=[q for q,c in quse.items() if c<200]
    print("qubits with <200 total appearances:", len(low), "min/max", (min(low),max(low)) if low else None)
    print("  of which >=840 (ancilla):", sum(1 for q in low if q>=840))
    print("  S-registers q<840:", sum(1 for q in low if q<840))

if __name__=="__main__":
    main()
