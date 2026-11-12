"""识别 '活量子 flag'：既是 CSWAP 控制位、又在后续被 HMR 的 qubit；统计每 stage 的 routing 份额。"""
from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path

KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_branch/eae.kmx")
STAGES = ("extract","synthesis","convert","scan","unconvert","unsynthesis","unextract")

def main():
    stage=None
    cswap_ctl=defaultdict(Counter)   # stage -> control qubit counts
    hmr_q=defaultdict(Counter)
    ccz_q=defaultdict(Counter)
    cx_1bit=defaultdict(Counter)
    for l in open(KMX, "r", encoding="utf-8", errors="replace"):
        if l.startswith("INFO_TAG "):
            tag=l.strip().split('"',2)[1]
            if tag.startswith("@enter:") and tag[7:] in STAGES: stage=tag[7:]
            elif tag.startswith("@exit:") and tag[6:]==stage: stage=None
            continue
        if not stage: continue
        p=l.split(); op=p[0]
        if op=="CSWAP": cswap_ctl[stage][p[1]]+=1
        elif op=="HMR": hmr_q[stage][p[1]]+=1
        elif op=="CCZ": ccz_q[stage][p[1]]+=1
    for st in STAGES:
        ctl=cswap_ctl[st]; hm=hmr_q[st]
        flag_ctl={q:c for q,c in ctl.items() if q in hm}
        data_ctl={q:c for q,c in ctl.items() if q not in hm}
        print(f"{st:12s} CSWAP={sum(ctl.values()):6d} distinct_ctl={len(ctl):5d} "
              f"ctl_also_HMR={sum(flag_ctl.values()):6d} ({len(flag_ctl)} qubits) "
              f"data_ctl={sum(data_ctl.values()):5d} HMR_sites={sum(hm.values()):6d}")
        if flag_ctl:
            print("    flag ctl qubits:", sorted(flag_ctl.items(), key=lambda kv:-kv[1])[:10])
    # 全局：哪些 qubit 只被用作 flag（出现次数少且曾 HMR）
    allhmr=Counter()
    for st in STAGES: allhmr.update(hmr_q[st])
    print("\nHMR 总量", sum(allhmr.values()), "distinct qubits", len(allhmr))
    print("HMR 目标在 ancilla(>=840):", sum(c for q,c in allhmr.items() if int(q[1:])>=840),
          " 在 S(<840):", sum(c for q,c in allhmr.items() if int(q[1:])<840))

if __name__=="__main__":
    main()
