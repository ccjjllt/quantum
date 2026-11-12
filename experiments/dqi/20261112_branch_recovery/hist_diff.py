"""extract vs unextract 的 segment-shape 直方图逐桶差分（gap=200）。"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
import importlib.util, sys

spec = importlib.util.spec_from_file_location("g", "experiments/dqi/20261112_branch_recovery/gadgets.py")
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)

def hist(stage):
    segs = g.collect(stage, gap=200)
    h = Counter()
    for s in segs: h[g.shape(s)] += 1
    return h, segs

def main():
    he,_ = hist("extract"); hu,_ = hist("unextract")
    keys = sorted(set(he)|set(hu), key=lambda k: -abs(k[0]*hu.get(k,0)-k[0]*he.get(k,0)))
    rows=[]
    for k in keys:
        ce, cu = he.get(k,0), hu.get(k,0)
        if ce==0 and cu==0: continue
        de, du = k[0]*ce, k[0]*cu
        rows.append({"shape":{"paid":k[0],"CCX":k[1],"CSWAP":k[2],"CCZ":k[3]},
                     "extract_count":ce,"unextract_count":cu,
                     "extract_T":de,"unextract_T":du,"delta_T":du-de})
    print(f"{'paid':>5} {'CCX':>5} {'CSW':>4} {'CCZ':>4} | {'ext_n':>6} {'unx_n':>6} | {'ext_T':>7} {'unx_T':>7} {'delta':>7}")
    for r in rows[:28]:
        s=r["shape"]
        print(f"{s['paid']:5d} {s['CCX']:5d} {s['CSWAP']:4d} {s['CCZ']:4d} | {r['extract_count']:6d} {r['unextract_count']:6d} | {r['extract_T']:7d} {r['unextract_T']:7d} {r['delta_T']:7d}")
    tot_e=sum(k[0]*v for k,v in he.items()); tot_u=sum(k[0]*v for k,v in hu.items())
    print("TOTAL", tot_e, tot_u, tot_u-tot_e)
    # 汇总：把 shape 归到 3 类
    def cls(k):
        paid,ccx,csw,ccz,carry = k
        if paid>=120 and ccz==0: return "big-CCX(>=120)"
        if paid==42 and ccx==42: return "mul12(42)"
        if paid==99 and ccx==99: return "mul24(99)"
        if paid==4 and ccx==3 and ccz==1: return "phase4(3C+CCZ)"
        if paid<=30: return "small(<=30)"
        return "other"
    ce=Counter(); cu=Counter()
    for k,v in he.items(): ce[cls(k)]+=k[0]*v
    for k,v in hu.items(): cu[cls(k)]+=k[0]*v
    print("\nclass totals:")
    for c in sorted(set(ce)|set(cu), key=lambda c:-(cu.get(c,0)-ce.get(c,0))):
        print(f"  {c:16s} extract={ce.get(c,0):7d} unextract={cu.get(c,0):7d} delta={cu.get(c,0)-ce.get(c,0):+7d}")
    Path("artifacts/20261112_branch_recovery/hist_diff.json").write_text(json.dumps({"gap":200,"rows":rows,"total":{"extract":tot_e,"unextract":tot_u}},indent=2))

if __name__=="__main__":
    main()
