"""全部 stage 的 segment-shape 直方图（gap=200），写 JSON。"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location("g", "experiments/dqi/20261112_branch_recovery/gadgets.py")
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)

STAGES=("extract","synthesis","convert","scan","unconvert","unsynthesis","unextract")
out={}
for st in STAGES:
    h=Counter()
    for s in g.collect(st, gap=200): h[g.shape(s)]+=1
    out[st]={"total_T":sum(k[0]*v for k,v in h.items()),
             "shapes":[{"paid":k[0],"CCX":k[1],"CSWAP":k[2],"CCZ":k[3],"count":v,"T":k[0]*v}
                       for k,v in sorted(h.items(), key=lambda kv:-kv[0][0]*kv[1])]}
    print(st, out[st]["total_T"], "segments", sum(h.values()))
Path("artifacts/20261112_branch_recovery/all_hist.json").write_text(json.dumps(out,indent=2))
# 汇总 42/99
tot42=sum(v["count"] for st in out for v in out[st]["shapes"] if (v["paid"],v["CCX"],v["CSWAP"],v["CCZ"])==(42,42,0,0))
tot99=sum(v["count"] for st in out for v in out[st]["shapes"] if (v["paid"],v["CCX"],v["CSWAP"],v["CCZ"])==(99,99,0,0))
print("42-blocks", tot42, "T", tot42*42, " 99-blocks", tot99, "T", tot99*99)
