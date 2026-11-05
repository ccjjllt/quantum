"""Template CCX redundancy via exact ANF re-extraction per dropped gate.
No sampling: ANF equality over all inputs. Read-only; no verifier."""
import itertools
import json
import sys
import time
from pathlib import Path

TMP = Path("/private/var/folders/9s/sdk1x32s58g8dycwh6c74bqc0000gp/T")
OUT = Path("artifacts/20261106_eeakernel_rewrite/template_redundancy.json")

t0 = time.monotonic()
d = json.load(open(TMP / "prod_template.json"))
ops = [tuple(p) for p in d["ops"]]
wires = d["wires"]
idx = {w: i for i, w in enumerate(wires)}
CAP = 500000


def anf(op_list):
    poly = {w: set([frozenset([idx[w]])]) for w in wires}
    for p in op_list:
        if p[0] == "CX":
            a, b = p[1], p[2]
            s = set(poly[b]) ^ set(poly[a])
            if len(s) > CAP:
                return None
            poly[b] = s
        elif p[0] == "CCX":
            a, b, t = p[1], p[2], p[3]
            prod = set()
            for x in poly[a]:
                for y in poly[b]:
                    prod.add(x | y)
                    if len(prod) > CAP:
                        return None
            s = set(poly[t]) ^ prod
            if len(s) > CAP:
                return None
            poly[t] = s
    return poly


base = anf(ops)
assert base is not None
ccx_pos = [i for i, p in enumerate(ops) if p[0] == "CCX"]
print(json.dumps({"n_ccx": len(ccx_pos), "base_ok": True}))
redundant = []
for k, pos in enumerate(ccx_pos):
    sub = [p for i, p in enumerate(ops) if i != pos]
    m = anf(sub)
    if m is None:
        print(json.dumps({"drop": k, "result": "blowup"}))
        continue
    same = all(m[w] == base[w] for w in wires)
    print(json.dumps({"drop": k, "op": list(ops[pos]), "redundant": same}))
    if same:
        redundant.append(k)
out = {"n_ccx": len(ccx_pos), "redundant": redundant,
       "wall_seconds": round(time.monotonic() - t0, 1)}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({"done": True, "redundant": redundant}))
