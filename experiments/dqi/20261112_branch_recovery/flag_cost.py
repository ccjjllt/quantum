"""统计 'flag 决策' 机器的 T 成本：X 前缀 + AND ladder + (HMR+CZ | del_and) 形态。
并给出：CSWAP routing、flag 供给的上界。
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path

KMX = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T/dqi_branch/eae.kmx")
STAGES=("extract","synthesis","convert","scan","unconvert","unsynthesis","unextract")

def main():
    lines=[]
    stage=None
    for l in open(KMX,"r",encoding="utf-8",errors="replace"):
        if l.startswith("INFO_TAG "):
            tag=l.strip().split('"',2)[1]
            if tag.startswith("@enter:") and tag[7:] in STAGES: stage=tag[7:]
            elif tag.startswith("@exit:") and tag[6:]==stage: stage=None
            continue
        if not stage or not l: continue
        if l.startswith(("APPEND","REGISTER","SEMANTIC","ANNOTATION")): continue
        lines.append((stage,l.split()))
    # 找 X-run 后接 CCX ladder 的模式
    stats=Counter(); ladder_cost=Counter(); n_sites=Counter()
    i=0; L=len(lines)
    while i<L:
        st,p=lines[i]
        if p[0]=="X":
            # X-run
            j=i
            xs=[]
            while j<L and lines[j][1][0]=="X" and lines[j][0]==st:
                xs.append(lines[j][1][1]); j+=1
            n=len(xs)
            if n>=4 and j<L and lines[j][1][0] in ("R","CCX"):
                # 往后找 ladder 的 CCX 数与 HMR/del_and
                k=j; ccx=0; has_hmr=False; has_ccz=False
                while k<L and k<j+4*n+40 and lines[k][0]==st:
                    op=lines[k][1][0]
                    if op=="CCX": ccx+=1
                    elif op=="HMR": has_hmr=True
                    elif op=="CCZ": has_ccz=True
                    elif op in ("BIT_STORE0","INFO_TAG"): pass
                    elif op=="CX" and ccx>0: break
                    k+=1
                # ladder 只认 n-1 或 n（含 copy-out）
                if ccx in (n-1,n,n+1) and (has_hmr or has_ccz):
                    stats[(st,"mbuzero" if has_hmr else "phasezero",n)]+=1
                    ladder_cost[st]+=ccx; n_sites[st]+=1
            i=j
        else:
            i+=1
    print("zero-flag / phase-zero ladder 站点：")
    tot=0
    for (st,kind,n),c in sorted(stats.items()):
        print(f"  {st:12s} {kind:10s} n={n:3d} sites={c:4d}  T={c*(n-1)}")
        tot+=c*(n-1)
    print("ladder 总 T ≈", tot)
    print("按 stage:", dict(ladder_cost), "站点:", dict(n_sites))
    print("CSWAP routing = 12012 (全电路)")
    print("上界：routing 12012 + ladder", tot, "=", 12012+tot)

if __name__=="__main__":
    main()
