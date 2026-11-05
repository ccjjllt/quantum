"""Boundary-span audit + norm-template exact redundancy. Read-only; no verifier."""
import itertools
import json
import re
import sys
from collections import Counter
from pathlib import Path

KMX = Path(sys.argv[1]) if len(sys.argv) > 1 else None
OUT = Path("artifacts/20261106_eeakernel_fusion/boundary_audit.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

GAPS = {"norm_scalar_gap": (2701056, 2701079),
        "scalar_products_gap": (2701668, 2702021),
        "products_norm_gap": (2702884, 2719477)}


def span_ops(lo, hi):
    ops = []
    with open(KMX) as f:
        for ln, line in enumerate(f, 1):
            if lo <= ln <= hi and not line.startswith(("INFO_TAG", "APPEND", "REGISTER")):
                ops.append(line.split())
    return ops


def main():
    assert KMX is not None and KMX.exists()
    out = {"gaps": {}, "norm_template": {}}
    for name, (lo, hi) in GAPS.items():
        ops = span_ops(lo, hi)
        kinds = Counter(p[0] for p in ops)
        wires = sorted({t for p in ops for t in p[1:] if t.startswith("q")}, key=lambda t: int(t[1:]))
        out["gaps"][name] = {"n_ops": len(ops), "op_kinds": dict(kinds), "n_wires": len(wires),
                             "has_R": "R" in kinds, "has_HMR": "HMR" in kinds,
                             "classical_exact_ok": not ("R" in kinds or "HMR" in kinds)}
        print(json.dumps({"gap": name, **out["gaps"][name]}))
    # norm template single+pair deletion (pure CX+CCX => ANF exact)
    with open(KMX) as f:
        lines = f.readlines()
    # first norm block ops (known span 2700837..2701055)
    ops = [l.split() for i, l in enumerate(lines, 1)
           if 2700837 <= i <= 2701055 and not l.startswith(("INFO_TAG", "APPEND", "REGISTER"))]
    assert all(p[0] in ("CX", "CCX") for p in ops), Counter(p[0] for p in ops)
    wires = sorted({t for p in ops for t in p[1:] if t.startswith("q")}, key=lambda t: int(t[1:]))
    idx = {w: i for i, w in enumerate(wires)}
    CAP = 600000

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
    ccx = [i for i, p in enumerate(ops) if p[0] == "CCX"]
    red1 = [k for k in ccx
            if (lambda m: m is not None and all(m[w] == base[w] for w in wires))
            (anf([p for i, p in enumerate(ops) if i != k]))]
    red2 = []
    for a, b in itertools.combinations(ccx, 2):
        m = anf([p for i, p in enumerate(ops) if i not in (a, b)])
        if m is not None and all(m[w] == base[w] for w in wires):
            red2.append([a, b])
    out["norm_template"] = {"n_ccx": len(ccx), "redundant_single": red1,
                            "pairs_tested": len(list(itertools.combinations(ccx, 2))),
                            "redundant_pairs": red2}
    print(json.dumps({"norm_template": out["norm_template"]}))
    OUT.write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
